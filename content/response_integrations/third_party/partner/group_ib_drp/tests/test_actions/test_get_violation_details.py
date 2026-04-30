"""Unit tests for the ``Get Violation Details`` action.

This action enriches each ``DestinationURL`` target entity with the full
violation payload from the DRP API. It builds a URL→UID map from the
current alert's security events and skips entities for which no UID can
be resolved. Per-entity exceptions degrade the result but never abort
the action; only an unhandled exception escalates to ``FAILED``.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..common import ACTIONS_PATH, load_script
from ..core.siemplify_mocks import FakeEntity, FakeSecurityEvent


@pytest.fixture
def gvd_module():
    return load_script(ACTIONS_PATH, "Get Violation Details.py", "GetViolationDetails")


def _violation_payload(uid: str, *, status="detected", subtype="phishing"):
    """Return a representative DRP ``violation`` raw_dict for a feed."""
    return {
        "id": uid,
        "brand": "ACME",
        "company": "ACME Corp",
        "link": f"https://drp.example.com/violations/{uid}",
        "images": [],
        "violation": {
            "uri": f"https://bad.example.com/{uid}",
            "status": status,
            "approveState": "approved",
            "violationType": "violation",
            "violationSubtype": subtype,
            "title": "Phishing site",
            "description": "Imitating ACME login page",
            "tags": ["phish"],
            "scores": [
                {"type": "domain", "score": 90},
                {"type": "risk", "score": 80},
            ],
            "firstDetected": "2026-01-01",
            "firstActive": "2026-01-02",
            "firstSolved": None,
            "dates": {"createdDate": "2026-01-01"},
            "stages": [],
            "workerCodes": ["w1"],
        },
    }


class TestGetViolationDetails:
    """Each branch of the action is its own test: a happy path, a missing
    UID, an empty alert, an API exception, and a non-URL entity that should
    be skipped silently."""

    def test_fetches_details_for_each_destination_url_and_emits_insights(
        self, gvd_module, action_siemplify_factory, fake_poller
    ):
        """Two URL entities both with mapped UIDs → both are fetched, both
        attached as JSON, both produce a case insight, and the action
        ends ``COMPLETED`` with ``result_value=True``."""

        url_a = "https://bad.example.com/a"
        url_b = "https://bad.example.com/b"
        entities = [
            FakeEntity(identifier=url_a, entity_type="DestinationURL"),
            FakeEntity(identifier=url_b, entity_type="DestinationURL"),
        ]
        events = [
            FakeSecurityEvent(additional_properties={"violation_url": url_a, "violation_uid": "uid-a"}),
            FakeSecurityEvent(additional_properties={"violation_url": url_b, "violation_uid": "uid-b"}),
        ]
        siemplify = action_siemplify_factory(target_entities=entities, security_events=events)

        responses = {
            "uid-a": _violation_payload("uid-a"),
            "uid-b": _violation_payload("uid-b", subtype="counterfeit"),
        }
        fake_poller.set_search_feed_side_effect(lambda feed_id: type("P", (), {"raw_dict": responses[feed_id]})())

        with (
            patch.object(gvd_module, "SiemplifyAction", return_value=siemplify),
            patch.object(gvd_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            gvd_module.main()

        feed_calls = [c.kwargs["feed_id"] for c in fake_poller.calls_to("search_feed_by_id")]
        assert feed_calls == ["uid-a", "uid-b"]

        siemplify.result.add_result_json.assert_called_once()
        attached_json = siemplify.result.add_result_json.call_args.args[0]
        attached = json.loads(attached_json)
        assert {row["id"] for row in attached} == {"uid-a", "uid-b"}
        assert {row["score_domain"] for row in attached} == {90}
        assert {row["score_risk"] for row in attached} == {80}

        assert siemplify.create_case_insight.call_count == 2

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_COMPLETED
        assert end["result_value"] is True

    def test_skips_non_destination_url_entities(self, gvd_module, action_siemplify_factory, fake_poller):
        """An entity of type ``IPAddress`` should be ignored entirely — no
        API call, no JSON row, no insight."""

        entities = [FakeEntity(identifier="1.2.3.4", entity_type="IPAddress")]
        siemplify = action_siemplify_factory(target_entities=entities, security_events=[])

        with (
            patch.object(gvd_module, "SiemplifyAction", return_value=siemplify),
            patch.object(gvd_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            gvd_module.main()

        assert fake_poller.calls_to("search_feed_by_id") == []
        siemplify.create_case_insight.assert_not_called()

        end = siemplify._end_calls[0]
        # No URL entities → result_value stays False, status stays COMPLETED.
        assert end["status"] == EXECUTION_STATE_COMPLETED
        assert end["result_value"] is False
        assert "No DestinationURL" in end["message"]

    def test_marks_failed_when_uid_missing_for_url_entity(self, gvd_module, action_siemplify_factory, fake_poller):
        """A URL entity that doesn't appear in the URL→UID map is reported,
        no API call is made, and the action ends ``FAILED``."""

        url = "https://bad.example.com/no-uid"
        entities = [FakeEntity(identifier=url, entity_type="DestinationURL")]
        siemplify = action_siemplify_factory(target_entities=entities, security_events=[])

        with (
            patch.object(gvd_module, "SiemplifyAction", return_value=siemplify),
            patch.object(gvd_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            gvd_module.main()

        assert fake_poller.calls_to("search_feed_by_id") == []

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_FAILED
        assert "No UID found" in end["message"]

    def test_marks_failed_when_search_feed_raises(self, gvd_module, action_siemplify_factory, fake_poller):
        """If ``search_feed_by_id`` raises for an entity we record the
        failure but don't crash; the action ends ``FAILED``."""

        url = "https://bad.example.com/x"
        entities = [FakeEntity(identifier=url, entity_type="DestinationURL")]
        events = [FakeSecurityEvent(additional_properties={"violation_url": url, "violation_uid": "uid-x"})]
        siemplify = action_siemplify_factory(target_entities=entities, security_events=events)

        with (
            patch.object(gvd_module, "SiemplifyAction", return_value=siemplify),
            patch.object(gvd_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            with fake_poller.fail_requests("DRP 500 error"):
                gvd_module.main()

        assert fake_poller.calls_to("search_feed_by_id") == [fake_poller.calls_to("search_feed_by_id")[0]]
        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_FAILED
        assert "Failed to fetch violation details" in end["message"]

    def test_url_uid_map_is_lowercased_for_case_insensitive_match(
        self, gvd_module, action_siemplify_factory, fake_poller
    ):
        """Entities are matched against the URL→UID map case-insensitively.
        DRP feeds and SOAR entities don't always agree on case."""

        url_event = "https://bad.EXAMPLE.com/abc"
        url_entity = "HTTPS://bad.example.COM/abc"
        entities = [FakeEntity(identifier=url_entity, entity_type="DestinationURL")]
        events = [FakeSecurityEvent(additional_properties={"violation_url": url_event, "violation_uid": "uid-x"})]
        siemplify = action_siemplify_factory(target_entities=entities, security_events=events)

        fake_poller.set_search_feed_response(_violation_payload("uid-x"))

        with (
            patch.object(gvd_module, "SiemplifyAction", return_value=siemplify),
            patch.object(gvd_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            gvd_module.main()

        feed_calls = [c.kwargs["feed_id"] for c in fake_poller.calls_to("search_feed_by_id")]
        assert feed_calls == ["uid-x"]

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_COMPLETED
        assert end["result_value"] is True

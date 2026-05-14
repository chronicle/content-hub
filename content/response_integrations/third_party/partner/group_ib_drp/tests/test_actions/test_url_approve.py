"""Unit tests for the ``URL-Approve`` action.

The action POSTs to ``violation/change-approve`` with ``approve=True``
for every ``DestinationURL`` entity that maps to a known violation UID.
Per-entity failures are recorded in the output message but do not abort
the action; the final status only flips to ``FAILED`` if at least one
entity could not be approved.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..common import ACTIONS_PATH, load_script
from ..core.siemplify_mocks import FakeEntity, FakeSecurityEvent


@pytest.fixture
def approve_module():
    return load_script(ACTIONS_PATH, "URL-Approve.py", "UrlApprove")


def _make_event(url: str, uid: str) -> FakeSecurityEvent:
    return FakeSecurityEvent(additional_properties={"violation_url": url, "violation_uid": uid})


class TestUrlApprove:
    """One test per outcome: full success, mixed (some fail), unmapped only,
    nothing-to-do, and verify the per-call payload shape."""

    def test_approves_every_mapped_destination_url_entity(self, approve_module, action_siemplify_factory, fake_poller):
        """Two URL entities, both with UIDs → two POSTs and ``COMPLETED``."""

        url_a, uid_a = "https://bad.example.com/a", "uid-a"
        url_b, uid_b = "https://bad.example.com/b", "uid-b"
        siemplify = action_siemplify_factory(
            target_entities=[
                FakeEntity(url_a, "DestinationURL"),
                FakeEntity(url_b, "DestinationURL"),
            ],
            security_events=[_make_event(url_a, uid_a), _make_event(url_b, uid_b)],
        )

        with (
            patch.object(approve_module, "SiemplifyAction", return_value=siemplify),
            patch.object(approve_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            approve_module.main()

        send_calls = fake_poller.calls_to("send_request")
        assert len(send_calls) == 2
        for call, expected_uid in zip(send_calls, [uid_a, uid_b]):
            assert call.args == ("violation/change-approve",)
            assert call.kwargs["method"] == "POST"
            assert call.kwargs["json"] == {"violationId": expected_uid, "approve": True}
            assert call.kwargs["params"] == {"q": None}

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_COMPLETED
        assert end["result_value"] is True
        assert "Approved" in end["message"]

    def test_records_failures_and_returns_failed(self, approve_module, action_siemplify_factory, fake_poller):
        """If any approve POST raises, action ends ``FAILED`` and the failed
        entity's identifier appears in the message."""

        url, uid = "https://bad.example.com/x", "uid-x"
        siemplify = action_siemplify_factory(
            target_entities=[FakeEntity(url, "DestinationURL")],
            security_events=[_make_event(url, uid)],
        )
        with (
            patch.object(approve_module, "SiemplifyAction", return_value=siemplify),
            patch.object(approve_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            with fake_poller.fail_requests("400 Bad Request"):
                approve_module.main()

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_FAILED
        assert "Failed:" in end["message"]
        assert url in end["message"]
        assert end["result_value"] is False

    def test_unmapped_entities_are_reported_but_action_completes(
        self, approve_module, action_siemplify_factory, fake_poller
    ):
        """An entity with no matching UID is reported but doesn't fail the
        action — there's nothing to approve, but no error either."""

        url = "https://bad.example.com/orphan"
        siemplify = action_siemplify_factory(
            target_entities=[FakeEntity(url, "DestinationURL")],
            security_events=[],
        )

        with (
            patch.object(approve_module, "SiemplifyAction", return_value=siemplify),
            patch.object(approve_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            approve_module.main()

        assert fake_poller.calls_to("send_request") == []

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_COMPLETED
        assert end["result_value"] is False
        assert "No matching violation UID" in end["message"]

    def test_no_destination_url_entities_emits_no_op_message(
        self, approve_module, action_siemplify_factory, fake_poller
    ):
        """Action invoked on a case with no URL entities → graceful no-op."""

        siemplify = action_siemplify_factory(
            target_entities=[FakeEntity("1.2.3.4", "IPAddress")],
            security_events=[],
        )

        with (
            patch.object(approve_module, "SiemplifyAction", return_value=siemplify),
            patch.object(approve_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            approve_module.main()

        end = siemplify._end_calls[0]
        assert end["message"] == "No DestinationURL entities to approve."
        assert end["status"] == EXECUTION_STATE_COMPLETED
        assert end["result_value"] is False

    def test_partial_success_returns_failed_but_marks_partial_truth(
        self, approve_module, action_siemplify_factory, fake_poller
    ):
        """One entity OK, one entity failing → action ends ``FAILED`` (because
        at least one failed) but ``result_value`` is True (because at least
        one was approved)."""

        url_a, uid_a = "https://bad.example.com/ok", "uid-ok"
        url_b, uid_b = "https://bad.example.com/bad", "uid-bad"
        siemplify = action_siemplify_factory(
            target_entities=[
                FakeEntity(url_a, "DestinationURL"),
                FakeEntity(url_b, "DestinationURL"),
            ],
            security_events=[_make_event(url_a, uid_a), _make_event(url_b, uid_b)],
        )

        def selective_send(endpoint, params=None, method=None, json=None, **_):
            if json["violationId"] == uid_b:
                raise Exception("simulated failure")
            return {"ok": True}

        fake_poller.set_send_request_side_effect(selective_send)

        with (
            patch.object(approve_module, "SiemplifyAction", return_value=siemplify),
            patch.object(approve_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            approve_module.main()

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_FAILED
        assert end["result_value"] is True
        assert "Approved" in end["message"]
        assert "Failed" in end["message"]

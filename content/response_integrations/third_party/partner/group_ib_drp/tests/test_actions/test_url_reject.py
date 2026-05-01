"""Unit tests for the ``URL-Reject`` action.

Mirror of ``URL-Approve`` but submits ``approve=False``. We re-cover the
same set of branches because the two actions are independently
maintained — a refactor that drifted reject behavior from approve
would otherwise slip through unnoticed.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..common import ACTIONS_PATH, load_script
from ..core.siemplify_mocks import FakeEntity, FakeSecurityEvent


@pytest.fixture
def reject_module():
    return load_script(ACTIONS_PATH, "URL-Reject.py", "UrlReject")


def _make_event(url: str, uid: str) -> FakeSecurityEvent:
    return FakeSecurityEvent(additional_properties={"violation_url": url, "violation_uid": uid})


class TestUrlReject:
    """Cover the same matrix of outcomes as ``URL-Approve`` and assert
    ``approve=False`` in every POST."""

    def test_rejects_every_mapped_destination_url_entity(self, reject_module, action_siemplify_factory, fake_poller):
        """Two URL entities, both with UIDs → two POSTs and ``COMPLETED``."""

        url, uid = "https://bad.example.com/a", "uid-a"
        siemplify = action_siemplify_factory(
            target_entities=[FakeEntity(url, "DestinationURL")],
            security_events=[_make_event(url, uid)],
        )

        with (
            patch.object(reject_module, "SiemplifyAction", return_value=siemplify),
            patch.object(reject_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            reject_module.main()

        send_calls = fake_poller.calls_to("send_request")
        assert len(send_calls) == 1
        assert send_calls[0].args == ("violation/change-approve",)
        assert send_calls[0].kwargs["method"] == "POST"
        assert send_calls[0].kwargs["json"] == {"violationId": uid, "approve": False}

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_COMPLETED
        assert end["result_value"] is True
        assert "Rejected" in end["message"]

    def test_records_failures_and_returns_failed(self, reject_module, action_siemplify_factory, fake_poller):
        """An API exception during reject → ``FAILED``."""

        url, uid = "https://bad.example.com/x", "uid-x"
        siemplify = action_siemplify_factory(
            target_entities=[FakeEntity(url, "DestinationURL")],
            security_events=[_make_event(url, uid)],
        )

        with (
            patch.object(reject_module, "SiemplifyAction", return_value=siemplify),
            patch.object(reject_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            with fake_poller.fail_requests("400 Bad Request"):
                reject_module.main()

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_FAILED
        assert "Failed:" in end["message"]
        assert url in end["message"]

    def test_unmapped_entities_are_reported_but_action_completes(
        self, reject_module, action_siemplify_factory, fake_poller
    ):
        """An entity with no matching UID is reported but doesn't fail the
        action — there's nothing to reject, but no error either."""

        url = "https://bad.example.com/orphan"
        siemplify = action_siemplify_factory(
            target_entities=[FakeEntity(url, "DestinationURL")],
            security_events=[],
        )

        with (
            patch.object(reject_module, "SiemplifyAction", return_value=siemplify),
            patch.object(reject_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            reject_module.main()

        assert fake_poller.calls_to("send_request") == []

        end = siemplify._end_calls[0]
        assert end["status"] == EXECUTION_STATE_COMPLETED
        assert "No matching violation UID" in end["message"]

    def test_no_destination_url_entities_emits_no_op_message(
        self, reject_module, action_siemplify_factory, fake_poller
    ):
        """Action invoked on a case with no URL entities → graceful no-op."""

        siemplify = action_siemplify_factory(
            target_entities=[FakeEntity("1.2.3.4", "IPAddress")],
            security_events=[],
        )

        with (
            patch.object(reject_module, "SiemplifyAction", return_value=siemplify),
            patch.object(reject_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            reject_module.main()

        end = siemplify._end_calls[0]
        assert end["message"] == "No DestinationURL entities to reject."
        assert end["status"] == EXECUTION_STATE_COMPLETED

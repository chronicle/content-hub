"""Unit tests for the ``DRP Violations Review Connector``.

Same shape as the violations connector but specifically scoped to the
``approveState=under_review`` (state ``3``) bucket. The defining
behaviour we lock down here is:

1. ``create_update_generator`` is invoked with ``approve_states=[3]``,
   regardless of any operator-supplied filters (the review connector
   doesn't expose those parameters at all).
2. ``script_name`` resolves to ``Config.GC_REVIEW_CONNECTOR_SCRIPT_NAME``.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ..common import CONNECTORS_PATH, load_script
from ..core.poller import FakePortion


@pytest.fixture
def conn_module():
    return load_script(
        CONNECTORS_PATH,
        "DRP Violations Review Connector.py",
        "DRPViolationsReviewConnector",
    )


def _conn_params(**overrides):
    base = {
        "Case name": "Violation Review",
        "Case type": "Violations Review",
        "Case severity": "High",
        "Start date": "2026-01-01",
        "API login": "u",
        "API key": "k",
        "API URL": "https://drp.example.com/client_api/",
        "Verify SSL": True,
    }
    base.update(overrides)
    return base


def _alert_info_stub(*_args, **_kwargs):
    class _AI:
        def __init__(self):
            self.display_id = ""
            self.ticket_id = ""
            self.source_grouping_identifier = ""
            self.name = ""
            self.rule_generator = ""
            self.start_time = 0
            self.end_time = 0
            self.priority = 0
            self.device_vendor = ""
            self.device_product = ""
            self.environment = ""
            self.events: list = []

    return _AI()


class TestReviewGather:
    """Lock the ``approve_states=[3]`` filter — drift here would surface
    *all* violations to review queues, defeating the connector's purpose."""

    def test_filters_to_under_review_state(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=42
        )
        fake_poller.set_update_portions([])

        with patch.object(conn_module, "GIBConnector") as gib_cls:
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            conn_module.gather_events(siemplify, start_date=None)

        gen = fake_poller.calls_to("create_update_generator")[0]
        assert gen.kwargs["approve_states"] == [3]
        assert gen.kwargs["sequpdate"] == 42
        assert "brands" not in gen.kwargs
        assert "subtypes" not in gen.kwargs
        assert "section" not in gen.kwargs
        assert "use_typo_squatting" not in gen.kwargs


class TestReviewMain:
    def test_main_uses_review_script_name_and_returns_alerts(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=5
        )
        fake_poller.set_update_portions(
            [
                FakePortion(
                    events=[
                        {"uid": "rev-1", "fake_uri": "https://review.example.com/1"},
                        {"uid": "rev-2", "fake_uri": "https://review.example.com/2"},
                    ],
                    sequpdate=8,
                )
            ]
        )

        with (
            patch.object(conn_module, "SiemplifyConnectorExecution", return_value=siemplify),
            patch.object(conn_module, "GIBConnector") as gib_cls,
            patch.object(conn_module, "AlertInfo", side_effect=_alert_info_stub),
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            conn_module.main()

        assert (
            siemplify.script_name
            == conn_module.Config.GC_REVIEW_CONNECTOR_SCRIPT_NAME
        )
        alerts = siemplify._returned_packages[0]
        assert [a.ticket_id for a in alerts] == ["rev-1", "rev-2"]
        assert all(a.priority == 80 for a in alerts)  # Case severity = High
        siemplify.save_timestamp.assert_called_once()

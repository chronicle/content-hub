"""Unit tests for the ``DRP Typosquatting Connector``.

The connector is a near-clone of ``DRP Violations Connector`` but with
two material differences we MUST cover:

1. ``create_update_generator`` is called with ``use_typo_squatting=True``,
   not with brand/approve/subtype filters.
2. ``script_name`` resolves to ``Config.GC_TYPOSQUATTING_CONNECTOR_SCRIPT_NAME``
   rather than the violations connector's script name.

Drift between the three connectors is the single most likely source of
production regressions; these tests pin the unique behavior down so a
future refactor that accidentally unifies them will fail loudly.
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
        "DRP Typosquatting Connector.py",
        "DRPTyposquattingConnector",
    )


def _conn_params(**overrides):
    base = {
        "Case name": "Typosquatting Domain",
        "Case type": "Typosquatting",
        "Case severity": "Medium",
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


class TestTyposquattingGather:
    """Verify the typosquatting filter is the *only* filter applied."""

    def test_passes_use_typo_squatting_true_and_no_brand_filters(
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
        assert gen.kwargs["use_typo_squatting"] is True
        assert gen.kwargs["sequpdate"] == 42
        assert "brands" not in gen.kwargs
        assert "approve_states" not in gen.kwargs
        assert "subtypes" not in gen.kwargs
        assert "section" not in gen.kwargs

    def test_returns_none_for_empty_generator(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=1
        )
        fake_poller.set_update_portions([])

        with patch.object(conn_module, "GIBConnector") as gib_cls:
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            assert conn_module.gather_events(siemplify, start_date=None) is None

    def test_persists_advanced_sequpdate(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=10
        )
        fake_poller.set_update_portions(
            [
                FakePortion(
                    events=[{"uid": "u1", "fake_uri": "https://typo.example.com/1"}],
                    sequpdate=11,
                )
            ]
        )

        with patch.object(conn_module, "GIBConnector") as gib_cls:
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            conn_module.gather_events(siemplify, start_date=None)

        siemplify.save_timestamp.assert_called_once()
        assert siemplify.save_timestamp.call_args.kwargs["new_timestamp"] == 11


class TestTyposquattingMain:
    """End-to-end: portions in → alerts out via ``return_package``."""

    def test_main_returns_alerts_with_typosquatting_script_name(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=5
        )
        fake_poller.set_update_portions(
            [
                FakePortion(
                    events=[{"uid": "u1", "fake_uri": "https://typo.example.com/1"}],
                    sequpdate=6,
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

        assert siemplify.script_name == conn_module.Config.GC_TYPOSQUATTING_CONNECTOR_SCRIPT_NAME
        assert len(siemplify._returned_packages) == 1
        alerts = siemplify._returned_packages[0]
        assert [a.ticket_id for a in alerts] == ["u1"]
        assert alerts[0].name.startswith("Typosquatting Domain:")
        assert alerts[0].rule_generator.startswith("Typosquatting:")

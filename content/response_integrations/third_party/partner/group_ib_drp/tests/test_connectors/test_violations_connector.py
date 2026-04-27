"""Unit tests for the ``DRP Violations Connector``.

The connector turns DRP violation feeds into SOAR ``AlertInfo`` objects.
It applies optional filters (brand IDs / approve states / subtypes /
section), iterates every API portion, dedupes via ``source_grouping_identifier`` and persists the highest seen ``sequpdate`` so the next
run resumes from the correct cursor.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ..common import CONNECTORS_PATH, load_script
from ..core.poller import FakePortion


@pytest.fixture
def conn_module():
    return load_script(
        CONNECTORS_PATH, "DRP Violations Connector.py", "DRPViolationsConnector"
    )


def _conn_params(**overrides):
    """Connector-side knob defaults that match the integration's YAML."""
    base = {
        "Case name": "Violation URL",
        "Case type": "Violations",
        "Case severity": "Medium",
        "Start date": "2026-01-01",
        "Brand IDs": "",
        "Approve States": "",
        "Subtypes": "",
        "Section": "",
        "API login": "u",
        "API key": "k",
        "API URL": "https://drp.example.com/client_api/",
        "Verify SSL": True,
    }
    base.update(overrides)
    return base


class TestGatherEvents:
    """``gather_events`` is the data path; cover bootstrap (no fetched
    timestamp), resume-from-timestamp, and the empty-portion case."""

    def test_bootstrap_uses_get_seq_update_dict_when_no_fetched_ts(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        """No prior timestamp → connector queries DRP for the seq update
        floor and feeds it to ``create_update_generator``."""

        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=None
        )
        fake_poller.set_seq_update_dict({"violation/list": 12345})
        fake_poller.set_update_portions(
            [
                FakePortion(
                    events=[
                        {"uid": "u1", "fake_uri": "https://bad.example.com/u1"},
                        {"uid": "u2", "fake_uri": "https://bad.example.com/u2"},
                    ],
                    sequpdate=99999,
                )
            ]
        )

        with patch.object(conn_module, "GIBConnector") as gib_cls:
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            events = conn_module.gather_events(siemplify, start_date="2026-01-01")

        assert {e["uid"] for e in events} == {"u1", "u2"}
        seq_calls = fake_poller.calls_to("get_seq_update_dict")
        assert seq_calls and seq_calls[0].kwargs["date"] == "2026-01-01"
        assert seq_calls[0].kwargs["collection_name"] == "violation/list"
        gen_call = fake_poller.calls_to("create_update_generator")[0]
        assert gen_call.kwargs["sequpdate"] == 12345
        siemplify.save_timestamp.assert_called_once()
        assert siemplify.save_timestamp.call_args.kwargs["new_timestamp"] == 99999

    def test_resumes_from_fetched_timestamp_when_present(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        """A persisted ``fetch_timestamp`` short-circuits the bootstrap call."""

        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=70000
        )
        fake_poller.set_update_portions(
            [
                FakePortion(
                    events=[{"uid": "u1", "fake_uri": "https://bad.example.com/u1"}],
                    sequpdate=70000,  # unchanged → no save_timestamp
                )
            ]
        )

        with patch.object(conn_module, "GIBConnector") as gib_cls:
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            conn_module.gather_events(siemplify, start_date="2026-01-01")

        assert fake_poller.calls_to("get_seq_update_dict") == []
        gen_call = fake_poller.calls_to("create_update_generator")[0]
        assert gen_call.kwargs["sequpdate"] == 70000
        siemplify.save_timestamp.assert_not_called()

    def test_returns_none_when_no_portions(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        """An empty generator yields ``None`` so ``main`` knows nothing to do."""

        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=1
        )
        fake_poller.set_update_portions([])

        with patch.object(conn_module, "GIBConnector") as gib_cls:
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            assert conn_module.gather_events(siemplify, start_date=None) is None

    def test_forwards_optional_filters_to_generator(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        """Brand/approve/subtypes/section filters are forwarded as-is."""

        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=10
        )
        fake_poller.set_update_portions([])

        with patch.object(conn_module, "GIBConnector") as gib_cls:
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            conn_module.gather_events(
                siemplify,
                start_date=None,
                brand_ids=["brand-1", "brand-2"],
                approve_states=[3],
                subtypes=[6],
                section=1,
            )

        gen = fake_poller.calls_to("create_update_generator")[0]
        assert gen.kwargs["brands"] == ["brand-1", "brand-2"]
        assert gen.kwargs["approve_states"] == [3]
        assert gen.kwargs["subtypes"] == [6]
        assert gen.kwargs["section"] == 1


class TestCreateAlert:
    """The connector-local helper that builds an ``AlertInfo`` for a
    violation event. Verify severity mapping, the deterministic
    ``source_grouping_identifier``, and the embedded URL event."""

    def test_severity_map_unknown_value_defaults_to_medium(
        self, conn_module, connector_siemplify_factory
    ):
        siemplify = connector_siemplify_factory(parameters=_conn_params())
        with patch.object(conn_module, "AlertInfo") as alert_info_cls:
            alert_info_cls.return_value = _alert_info_stub()
            alert = conn_module.create_alert(
                siemplify=siemplify,
                uid="uid-x",
                fake_uri="https://bad.example.com/x",
                alert_name=None,
                alert_type=None,
                alert_severity="UNKNOWN_SEVERITY",
            )
        assert alert.priority == 60

    def test_uses_uid_as_source_grouping_identifier(
        self, conn_module, connector_siemplify_factory
    ):
        siemplify = connector_siemplify_factory(parameters=_conn_params())
        with patch.object(conn_module, "AlertInfo") as alert_info_cls:
            alert_info_cls.return_value = _alert_info_stub()
            alert = conn_module.create_alert(
                siemplify=siemplify,
                uid="uid-x",
                fake_uri="https://bad.example.com/x",
                alert_name="Violation URL",
                alert_type="Violations",
                alert_severity="High",
            )
        assert alert.ticket_id == "uid-x"
        assert alert.source_grouping_identifier == "uid-x"
        assert alert.priority == 80
        assert alert.name == "Violation URL: bad.example.com"
        assert alert.rule_generator == "Violations: bad.example.com"

    def test_appends_destination_url_event_with_uid(
        self, conn_module, connector_siemplify_factory
    ):
        siemplify = connector_siemplify_factory(parameters=_conn_params())
        with patch.object(conn_module, "AlertInfo") as alert_info_cls:
            alert_info_cls.return_value = _alert_info_stub()
            alert = conn_module.create_alert(
                siemplify=siemplify,
                uid="uid-x",
                fake_uri="https://bad.example.com/x?p=1",
                alert_name="Violation URL",
                alert_type="Violations",
                alert_severity="Critical",
            )
        assert len(alert.events) == 1
        ev = alert.events[0]
        assert ev["event_type"] == "DestinationURL"
        assert ev["violation_url"] == "https://bad.example.com/x?p=1"
        assert ev["violation_uid"] == "uid-x"
        assert alert.priority == 100


class TestMain:
    """End-to-end: portions in → alerts out via ``return_package``."""

    def test_main_returns_alerts_for_each_event(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=10
        )
        fake_poller.set_update_portions(
            [
                FakePortion(
                    events=[
                        {"uid": "u1", "fake_uri": "https://bad.example.com/u1"},
                        {"uid": "u2", "fake_uri": "https://bad.example.com/u2"},
                    ],
                    sequpdate=70,
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

        assert len(siemplify._returned_packages) == 1
        alerts = siemplify._returned_packages[0]
        assert len(alerts) == 2
        assert {a.ticket_id for a in alerts} == {"u1", "u2"}

    def test_main_skips_overflow_alerts(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=1, is_overflow=True
        )
        fake_poller.set_update_portions(
            [
                FakePortion(
                    events=[{"uid": "u1", "fake_uri": "https://bad.example.com/u1"}],
                    sequpdate=2,
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

        assert siemplify._returned_packages == [[]]

    def test_main_skips_events_missing_uid_or_uri(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        """An event without ``uid`` or ``fake_uri`` is logged & skipped."""

        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=1
        )
        fake_poller.set_update_portions(
            [
                FakePortion(
                    events=[
                        {"uid": "u1", "fake_uri": ""},
                        {"uid": "", "fake_uri": "https://bad.example.com/x"},
                        {"uid": "u3", "fake_uri": "https://bad.example.com/u3"},
                    ],
                    sequpdate=2,
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

        alerts = siemplify._returned_packages[0]
        assert [a.ticket_id for a in alerts] == ["u3"]

    def test_main_handles_gather_events_exception(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        """A failure in ``gather_events`` must not crash the connector;
        an empty package is returned and the exception is logged."""

        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=1
        )

        with (
            patch.object(conn_module, "SiemplifyConnectorExecution", return_value=siemplify),
            patch.object(conn_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            with fake_poller.fail_requests("DRP API down"):
                conn_module.main()

        siemplify.LOGGER.exception.assert_called()
        assert siemplify._returned_packages == [[]]


class TestParameterParsing:
    """Verify the connector parses the comma-separated parameter strings
    into the typed lists it forwards to the generator."""

    def test_parses_comma_separated_brand_ids_approve_states_and_subtypes(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        params = _conn_params(**{
            "Brand IDs": "brand1, brand2 ,brand3",
            "Approve States": "1,3",
            "Subtypes": "6,7",
            "Section": "1",
        })
        siemplify = connector_siemplify_factory(parameters=params, fetched_timestamp=1)
        fake_poller.set_update_portions([])

        with (
            patch.object(conn_module, "SiemplifyConnectorExecution", return_value=siemplify),
            patch.object(conn_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            conn_module.main()

        gen = fake_poller.calls_to("create_update_generator")[0]
        assert gen.kwargs["brands"] == ["brand1", "brand2", "brand3"]
        assert gen.kwargs["approve_states"] == [1, 3]
        assert gen.kwargs["subtypes"] == [6, 7]
        assert gen.kwargs["section"] == 1

    def test_blank_filters_pass_through_as_none(
        self, conn_module, connector_siemplify_factory, fake_poller
    ):
        siemplify = connector_siemplify_factory(
            parameters=_conn_params(), fetched_timestamp=1
        )
        fake_poller.set_update_portions([])

        with (
            patch.object(conn_module, "SiemplifyConnectorExecution", return_value=siemplify),
            patch.object(conn_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            conn_module.main()

        gen = fake_poller.calls_to("create_update_generator")[0]
        assert gen.kwargs["brands"] is None
        assert gen.kwargs["approve_states"] is None
        assert gen.kwargs["subtypes"] is None
        assert gen.kwargs["section"] is None


class TestGetDefaultDate:
    """Helper used when the operator leaves ``Start date`` blank."""

    def test_get_default_date_returns_yyyy_mm_dd(self, conn_module):
        date = conn_module.get_default_date(days=1)
        assert len(date) == 10
        assert date[4] == "-" and date[7] == "-"


def _alert_info_stub(*_args, **_kwargs):
    """Build a real-shape stand-in for ``AlertInfo``.

    The connector pokes at attributes (``display_id``, ``ticket_id``,
    ``source_grouping_identifier``, ``name``, ``rule_generator``,
    ``start_time``, ``end_time``, ``priority``, ``device_vendor``,
    ``device_product``, ``environment``) and an ``events`` list. A simple
    ``types.SimpleNamespace`` would lose the ``events.append`` semantics,
    so we use a real class with the right defaults.
    """

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

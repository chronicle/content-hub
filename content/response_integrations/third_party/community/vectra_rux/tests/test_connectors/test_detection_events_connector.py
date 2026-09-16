from __future__ import annotations

import types

import pytest

from constants import DEFAULT_DEVICE_PRODUCT, RULE_GENERATOR, SEVERITY_MAP
from datamodels import DetectionEvent
from tests.common import load_connector
from tests.core.product import detection_event
from tests.test_connectors.conftest import run_connector
from TIPCommon.smp_io import write_ids
from UtilsManager import get_detection_alert_id
from VectraRUXExceptions import InvalidIntegerException, VectraRUXException
from VectraRUXParser import VectraRUXParser

CONNECTOR_NAME = "Vectra RUX - Detection Events Connector"

DEFAULT_PARAMETERS = {
    "API Root": "https://test.vectra.ai",
    "Client ID": "test-client-id",
    "Client Secret": "test-client-secret",
    "Environment Field Name": "",
    "Environment Regex Pattern": "",
    "Max Hours Backwards": "0",
    "Entity Type": "Host,Account",
    "Unresolved Priority": "false",
    "Include Triaged": "false",
    "Limit": "",
    "PythonProcessTimeout": "1200",
    "DeviceProductField": "Vectra RUX",
}

PARSER = VectraRUXParser()


def build_event(**overrides) -> DetectionEvent:
    """Build a DetectionEvent the same way the connector does: raw JSON
    (from the canned mock, with overrides) through the real parser.
    """
    return PARSER.build_detection_event_object(detection_event(**overrides))


class TestValidateInputParams:
    """`validate_input_params` is a pure function - no Siemplify/API mocking needed."""

    def test_rejects_invalid_entity_type(self):
        connector_module = load_connector(CONNECTOR_NAME)
        with pytest.raises(VectraRUXException, match="Entity type"):
            connector_module.validate_input_params("Server", "0", "")

    def test_rejects_hours_backwards_over_max(self):
        connector_module = load_connector(CONNECTOR_NAME)
        with pytest.raises(VectraRUXException, match="must not exceed 120 hours"):
            connector_module.validate_input_params("Host", "121", "")

    def test_rejects_zero_limit(self):
        connector_module = load_connector(CONNECTOR_NAME)
        with pytest.raises(InvalidIntegerException):
            connector_module.validate_input_params("Host", "0", "0")


class TestFirstRun:
    def test_creates_alert_from_mocked_event(self, connector, mock_session, product):
        connector_module = load_connector(CONNECTOR_NAME)

        alerts = run_connector(connector_module, connector, DEFAULT_PARAMETERS, is_test_run=True)

        assert len(alerts) == 1
        assert alerts[0].ticket_id == get_detection_alert_id(39902, 7362603)


class TestTriagedFiltering:
    def test_triaged_event_is_dropped_when_include_triaged_is_false(
        self, connector, mock_session, product,
    ):
        triaged_event = detection_event(id=1000, detection_id=100, triaged=True)
        untriaged_event = detection_event(id=1001, detection_id=101, triaged=False)
        product.set_detection_events([triaged_event, untriaged_event], remaining_count=0)
        parameters = {**DEFAULT_PARAMETERS, "Include Triaged": "false"}
        connector_module = load_connector(CONNECTOR_NAME)

        alerts = run_connector(connector_module, connector, parameters, is_test_run=True)

        assert len(alerts) == 1
        assert alerts[0].ticket_id == get_detection_alert_id(101, 1001)

    def test_triaged_event_is_kept_when_include_triaged_is_true(
        self, connector, mock_session, product,
    ):
        # is_test_run=False: with is_test_run=True the connector loop stops
        # after the first successfully processed event, which would hide a
        # second (previously-filtered) event surviving the manager-level
        # triaged check.
        triaged_event = detection_event(id=1000, detection_id=100, triaged=True)
        untriaged_event = detection_event(id=1001, detection_id=101, triaged=False)
        product.set_detection_events([triaged_event, untriaged_event], remaining_count=0)
        parameters = {**DEFAULT_PARAMETERS, "Include Triaged": "true"}
        connector_module = load_connector(CONNECTOR_NAME)

        alerts = run_connector(connector_module, connector, parameters, is_test_run=False)

        assert {alert.ticket_id for alert in alerts} == {
            get_detection_alert_id(100, 1000),
            get_detection_alert_id(101, 1001),
        }


class TestDuplicateFiltering:
    def test_duplicate_event_already_in_existing_ids_is_skipped(
        self, connector, mock_session, product,
    ):
        event = detection_event(id=7362603, detection_id=39902, triaged=False)
        product.set_detection_events([event], remaining_count=0)
        write_ids(connector, [get_detection_alert_id(39902, 7362603)])
        connector_module = load_connector(CONNECTOR_NAME)

        alerts = run_connector(connector_module, connector, DEFAULT_PARAMETERS, is_test_run=True)

        assert alerts == []

    def test_non_duplicate_event_is_kept(self, connector, mock_session, product):
        event = detection_event(id=7362603, detection_id=39902, triaged=False)
        product.set_detection_events([event], remaining_count=0)
        write_ids(connector, [get_detection_alert_id(11111, 22222)])
        connector_module = load_connector(CONNECTOR_NAME)

        alerts = run_connector(connector_module, connector, DEFAULT_PARAMETERS, is_test_run=True)

        assert len(alerts) == 1
        assert alerts[0].ticket_id == get_detection_alert_id(39902, 7362603)


class TestUnresolvedPriorityFiltering:
    """`Unresolved Priority` isn't filtered client-side - it's forwarded
    as-is to the events/detections API, which does the actual filtering.
    """

    def test_unresolved_priority_true_is_forwarded_to_the_api(self, connector, mock_session, product):
        parameters = {**DEFAULT_PARAMETERS, "Unresolved Priority": "true"}
        connector_module = load_connector(CONNECTOR_NAME)

        run_connector(connector_module, connector, parameters, is_test_run=True)

        events_request = next(
            r for r in mock_session.request_history if r["url"].endswith("/events/detections")
        )
        assert events_request["params"]["unresolved_priority"] is True

    def test_unresolved_priority_false_is_forwarded_to_the_api(self, connector, mock_session, product):
        parameters = {**DEFAULT_PARAMETERS, "Unresolved Priority": "false"}
        connector_module = load_connector(CONNECTOR_NAME)

        run_connector(connector_module, connector, parameters, is_test_run=True)

        events_request = next(
            r for r in mock_session.request_history if r["url"].endswith("/events/detections")
        )
        assert events_request["params"]["unresolved_priority"] is False


class TestAllDetectionStatusesAreCreated:
    """Detection Status filtering was removed from the connector, so an
    event must turn into an alert regardless of its `investigation_status`.
    """

    @pytest.mark.parametrize(
        "investigation_status",
        ["open", "acknowledged", "escalated", "paused", "closed", "expired"],
    )
    def test_alert_is_created_for_every_detection_status(
        self, connector, mock_session, product, investigation_status,
    ):
        event = detection_event(
            id=1000, detection_id=100, investigation_status=investigation_status,
        )
        product.set_detection_events([event], remaining_count=0)
        connector_module = load_connector(CONNECTOR_NAME)

        alerts = run_connector(connector_module, connector, DEFAULT_PARAMETERS, is_test_run=True)

        assert len(alerts) == 1
        assert alerts[0].ticket_id == get_detection_alert_id(100, 1000)


class TestAllChangeTypesAreCreated:
    """The connector doesn't filter on `change_type` - an event must turn
    into an alert regardless of which change it represents.
    """

    @pytest.mark.parametrize(
        "change_type",
        ["new", "append", "adjust", "triage", "investigation_status", "state"],
    )
    def test_alert_is_created_for_every_change_type(
        self, connector, mock_session, product, change_type,
    ):
        event = detection_event(id=1000, detection_id=100, change_type=change_type)
        product.set_detection_events([event], remaining_count=0)
        connector_module = load_connector(CONNECTOR_NAME)

        alerts = run_connector(connector_module, connector, DEFAULT_PARAMETERS, is_test_run=True)

        assert len(alerts) == 1
        assert alerts[0].ticket_id == get_detection_alert_id(100, 1000)


class TestGetSiemplifySeverity:
    """`get_siemplify_severity` picks its urgency field by entity type, then
    buckets the score into a Siemplify severity via if/else thresholds.
    """

    def test_uses_src_host_urgency_score_for_host_type(self):
        event = build_event(type="host", src_host={"urgency_score": 90})
        assert event.get_siemplify_severity() == SEVERITY_MAP["critical"]

    def test_uses_src_account_urgency_score_for_non_host_type(self):
        event = build_event(type="account", src_account={"urgency_score": 90})
        assert event.get_siemplify_severity() == SEVERITY_MAP["critical"]

    def test_missing_urgency_score_returns_minus_one(self):
        event = build_event(type="host", src_host={})
        assert event.get_siemplify_severity() == -1

    @pytest.mark.parametrize(
        "urgency_score, expected_severity",
        [
            (80, SEVERITY_MAP["critical"]),
            (79, SEVERITY_MAP["high"]),
            (61, SEVERITY_MAP["high"]),
            (60, SEVERITY_MAP["medium"]),
            (31, SEVERITY_MAP["medium"]),
            (30, SEVERITY_MAP["low"]),
            (0, SEVERITY_MAP["low"]),
        ],
    )
    def test_urgency_score_threshold_boundaries(self, urgency_score, expected_severity):
        event = build_event(type="host", src_host={"urgency_score": urgency_score})
        assert event.get_siemplify_severity() == expected_severity

class TestCreateEvent:
    """`create_event` derives `name`/`CategoryOutcome` with an `or` fallback
    and stamps a handful of fixed fields.
    """

    BASE_EVENT = {
        "event_timestamp": "2026-07-28T03:09:07Z",
        "detection_id": 39902,
        "type": "host",
    }

    def test_name_uses_detection_type_when_present(self):
        event = {**self.BASE_EVENT, "detection_type": "Hidden HTTPS Tunnel", "category": "command_and_control"}
        result = DetectionEvent.create_event(event)
        assert result["name"] == "Hidden HTTPS Tunnel"

    def test_name_falls_back_to_detection_id_when_detection_type_missing(self):
        event = {**self.BASE_EVENT, "detection_type": "", "category": "command_and_control"}
        result = DetectionEvent.create_event(event)
        assert result["name"] == "Detection 39902"

    def test_category_outcome_uses_category_when_present(self):
        event = {**self.BASE_EVENT, "detection_type": "x", "category": "command_and_control"}
        result = DetectionEvent.create_event(event)
        assert result["CategoryOutcome"] == "command_and_control"

    def test_category_outcome_falls_back_to_na_when_category_missing(self):
        event = {**self.BASE_EVENT, "detection_type": "x", "category": ""}
        result = DetectionEvent.create_event(event)
        assert result["CategoryOutcome"] == "N/A"

    def test_fixed_and_copied_fields(self):
        event = {**self.BASE_EVENT, "detection_type": "x", "category": "command_and_control"}
        result = DetectionEvent.create_event(event)
        assert result["DeviceProduct"] == DEFAULT_DEVICE_PRODUCT
        assert result["SourceSystemName"] == "Vectra RUX"
        assert result["SourceType"] == "Vectra RUX"
        assert result["EntityType"] == "host"


class TestGetAlertInfo:
    """`get_alert_info` computes several `AlertInfo` fields from the event
    plus an `or` fallback for `device_product`.
    """

    class FakeEnvironmentCommon:
        def __init__(self, environment="Default Environment"):
            self.environment = environment
            self.received_raw_data = None

        def get_environment(self, raw_data):
            self.received_raw_data = raw_data
            return self.environment

    def test_device_product_uses_configured_field_when_present(self):
        event = build_event(d_type_vname="Custom Product")
        alert_info = types.SimpleNamespace()

        event.get_alert_info(alert_info, self.FakeEnvironmentCommon(), device_product_field="d_type_vname")

        assert alert_info.device_product == "Custom Product"

    def test_device_product_falls_back_to_default_when_field_missing(self):
        event = build_event()
        alert_info = types.SimpleNamespace()

        event.get_alert_info(alert_info, self.FakeEnvironmentCommon(), device_product_field="no_such_field")

        assert alert_info.device_product == DEFAULT_DEVICE_PRODUCT

    def test_device_product_falls_back_to_default_when_field_is_empty(self):
        event = build_event(d_type_vname="")
        alert_info = types.SimpleNamespace()

        event.get_alert_info(alert_info, self.FakeEnvironmentCommon(), device_product_field="d_type_vname")

        assert alert_info.device_product == DEFAULT_DEVICE_PRODUCT

    def test_ticket_id_and_display_id_match_detection_alert_id(self):
        event = build_event(detection_id=39902, id=7362603)
        alert_info = types.SimpleNamespace()

        event.get_alert_info(alert_info, self.FakeEnvironmentCommon(), device_product_field="no_such_field")

        expected = get_detection_alert_id(39902, 7362603)
        assert alert_info.ticket_id == expected
        assert alert_info.display_id == expected

    def test_rule_generator_and_source_grouping_identifier(self):
        event = build_event(entity_uid="test-host-1", detection_id=39902)
        alert_info = types.SimpleNamespace()

        event.get_alert_info(alert_info, self.FakeEnvironmentCommon(), device_product_field="no_such_field")

        assert alert_info.rule_generator == f"{RULE_GENERATOR}: test-host-1"
        assert alert_info.source_grouping_identifier == "detection#39902"

    def test_environment_delegates_to_environment_common_with_raw_data(self):
        event = build_event()
        alert_info = types.SimpleNamespace()
        environment_common = self.FakeEnvironmentCommon(environment="EU")

        event.get_alert_info(alert_info, environment_common, device_product_field="no_such_field")

        assert alert_info.environment == "EU"
        assert environment_common.received_raw_data == event.raw_data

    def test_priority_delegates_to_get_siemplify_severity(self):
        event = build_event(type="host", src_host={"urgency_score": 90})
        alert_info = types.SimpleNamespace()

        event.get_alert_info(alert_info, self.FakeEnvironmentCommon(), device_product_field="no_such_field")

        assert alert_info.priority == SEVERITY_MAP["critical"]

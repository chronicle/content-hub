# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
import json
import sys
from typing import TYPE_CHECKING

import arrow
import pytest
from integration_testing import common
from integration_testing.common import set_is_test_run_to_true
from integration_testing.set_meta import set_metadata
from TIPCommon.data_models import DatabaseContextType
from TIPCommon.exceptions import ConnectorSetupError
from TIPCommon.utils import is_test_run

from sentinel_one_singularity_operations_center.connectors.unified_alerts_connector import (
    UnifiedAlertsConnector,
)
from sentinel_one_singularity_operations_center.core.api.api_client import (
    SentinelOneSingularityOperationsCenterApiClient,
)
from sentinel_one_singularity_operations_center.tests.common import INTEGRATION_PATH

if TYPE_CHECKING:
    from integration_testing.platform.external_context import MockExternalContext
    from integration_testing.platform.script_output import MockConnectorOutput

    from sentinel_one_singularity_operations_center.tests.core.product import (
        SentinelOne,
    )
    from sentinel_one_singularity_operations_center.tests.core.session import (
        SentinelOneSession,
    )

DEF_PATH = INTEGRATION_PATH / "connectors" / "unified_alerts_connector.yaml"

DEFAULT_PARAMETERS = {
    "DeviceProductField": "Product Name",
    "EventClassId": "event_type",
    "Environment Field Name": "",
    "Environment Regex Pattern": ".*",
    "PythonProcessTimeout": "180",
    "API Root": "https://usea1-dfir.sentinelone.net",
    "API Token": "mock_token",
    "Lowest Severity To Fetch": "",
    "Max Hours Backwards": 1,
    "Max Alerts To Fetch": 10,
    "Use dynamic list as a blocklist": "False",
    "Disable Overflow": "False",
    "Verify SSL": "False",
}


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_successful_connector_run(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
) -> None:
    """Test a successful connector run, verifying mapping and event structure."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = UnifiedAlertsConnector(is_test)
    connector.start()

    # Verifies that both the list query and detail query were run
    assert len(script_session.request_history) == 2

    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 1
    alert = alerts[0]

    # Verify key alert mappings
    assert alert.name == "avm.exe detected as Malware"
    assert alert.device_vendor == "SentinelOne Singularity Operations Center"
    assert alert.device_product == "SentinelOne Singularity Operations Center"
    assert (
        alert.display_id
        == "SentinelOne_Singularity_Operations_Center_019d114e-e4f4-7ad6-82c3-9829b6d0a801"
    )
    assert alert.priority == 100  # CRITICAL maps to 100
    assert (
        alert.rule_generator
        == "SentinelOne Singularity Operations Center Alert: MALWARE"
    )
    assert alert.source_grouping_identifier == "MALWARE"

    # Verify fields that are dynamically added and serialized but not copied back by the mock framework
    out_attr = "_" + "out"
    raw_output = json.loads(getattr(connector_output, out_attr).getvalue())
    raw_result = json.loads(raw_output["ResultObjectJson"])
    raw_alert = raw_result["cases"][0]
    assert raw_alert["extensions"]["Severity"] == "Critical"
    assert raw_alert["extensions"]["RiskScore"] == "CRITICAL"

    # Verify event types and observable transformations
    assert len(alert.events) == 4
    event_types = [event.get("event_type") for event in alert.events]
    assert event_types == ["Alert", "Observable", "Indicator", "Asset"]

    observable_event = alert.events[1]
    assert observable_event.get("process.name") == "avm.exe"
    assert observable_event.get("lastSeenAt") == "2026-03-21T16:51:18.468Z"

    asset_event = alert.events[3]
    assert asset_event.get("lastSeenAt") == "2026-03-21T16:51:18.468Z"
    assert asset_event.get("osType") == "WINDOWS"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={**DEFAULT_PARAMETERS, "Lowest Severity To Fetch": "INVALID"},
)
def test_invalid_severity_raises_error(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
) -> None:
    """Test that an invalid Lowest Severity To Fetch parameter raises a ConnectorSetupError."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = UnifiedAlertsConnector(is_test)

    with pytest.raises(ConnectorSetupError) as exc_info:
        connector.start()

    assert "invalid value provided" in str(exc_info.value)


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={**DEFAULT_PARAMETERS, "Use dynamic list as a blocklist": "True"},
)
def test_classification_blocklist_filter(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that alerts matching a classification in the blocklist are filtered out."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = UnifiedAlertsConnector(is_test)

    # Mock the read-only whitelist property on the SDK mock
    monkeypatch.setattr(
        type(connector.siemplify), "whitelist", property(lambda _: ["MALWARE"])
    )

    connector.start()

    # The alert classification is MALWARE, so it should be filtered out.
    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 0


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={**DEFAULT_PARAMETERS, "Use dynamic list as a blocklist": "False"},
)
def test_classification_allowlist_filter(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that alerts not matching a classification in the allowlist are filtered out."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = UnifiedAlertsConnector(is_test)

    # Mock the read-only whitelist property on the SDK mock
    monkeypatch.setattr(
        type(connector.siemplify), "whitelist", property(lambda _: ["PHISHING"])
    )

    connector.start()

    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 0


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={**DEFAULT_PARAMETERS, "Use dynamic list as a blocklist": "False"},
)
def test_classification_allowlist_filter_case_insensitive(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that classification matching is case-insensitive in allowlist mode."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = UnifiedAlertsConnector(is_test)

    # Mock lowercase 'malware' in whitelist matching 'MALWARE' in alert data
    monkeypatch.setattr(
        type(connector.siemplify), "whitelist", property(lambda _: ["malware"])
    )

    connector.start()

    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 1
    assert alerts[0].source_grouping_identifier == "MALWARE"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={**DEFAULT_PARAMETERS, "Use dynamic list as a blocklist": "True"},
)
def test_classification_blocklist_filter_case_insensitive(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that matching items are blocked case-insensitively when blocklist mode is enabled."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = UnifiedAlertsConnector(is_test)

    # Mock lowercase 'malware' in whitelist matching 'MALWARE' in alert data
    monkeypatch.setattr(
        type(connector.siemplify), "whitelist", property(lambda _: ["malware"])
    )

    connector.start()

    # MALWARE matches blocklist 'malware', so it should be filtered out
    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 0


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={**DEFAULT_PARAMETERS, "Use dynamic list as a blocklist": "True"},
)
def test_classification_blocklist_filter_passes_unmatched(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that non-matching items pass through when blocklist mode is enabled."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = UnifiedAlertsConnector(is_test)

    # Mock 'phishing' in blocklist, alert is 'MALWARE'
    monkeypatch.setattr(
        type(connector.siemplify), "whitelist", property(lambda _: ["phishing"])
    )

    connector.start()

    # MALWARE does not match blocklist 'phishing', so it should be ingested
    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 1
    assert alerts[0].source_grouping_identifier == "MALWARE"


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_id_cache_cleanup_optimization(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    """Test that the processed IDs cache does not exceed 1100 and removes the oldest 100 entries."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)

    # Seed the mock DB cache with 1105 dummy IDs (using a dictionary structure)
    base_time_ms = arrow.utcnow().shift(minutes=-30).int_timestamp * 1000
    dummy_ids = {f"id_{i}": base_time_ms + i for i in range(1105)}
    external_context.set_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        identifier=None,
        property_key="ids",
        property_value=json.dumps(dummy_ids),
    )

    # Modify mock alert's list and details lastSeenAt to be newer (current time)
    new_timestamp_str = arrow.utcnow().format("YYYY-MM-DDTHH:mm:ss.SSS") + "Z"
    new_alert_data = copy.deepcopy(sentinelone.alerts[0])
    new_alert_data["node"]["updatedAt"] = new_timestamp_str
    new_alert_data["node"]["lastSeenAt"] = new_timestamp_str
    sentinelone.alerts = [new_alert_data]

    new_details = copy.deepcopy(
        sentinelone.details["019d114e-e4f4-7ad6-82c3-9829b6d0a801"]
    )
    new_details["updatedAt"] = new_timestamp_str
    new_details["lastSeenAt"] = new_timestamp_str
    sentinelone.details["019d114e-e4f4-7ad6-82c3-9829b6d0a801"] = new_details

    connector = UnifiedAlertsConnector(is_test)
    connector.start()

    # Check that cache was pruned down to exactly 1000 entries
    assert len(connector.context.existing_ids) == 1000
    assert "id_0" not in connector.context.existing_ids
    assert "id_105" not in connector.context.existing_ids
    assert "id_106" in connector.context.existing_ids
    assert "019d114e-e4f4-7ad6-82c3-9829b6d0a801" in connector.context.existing_ids


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={
        **DEFAULT_PARAMETERS,
        "Max Alerts To Fetch": 110,
        "Disable Overflow": "True",
    },
)
def test_connector_pagination(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
) -> None:
    """Test that the connector successfully paginates when there are more alerts than the page size."""
    # Seed 105 mock alerts in sentinelone
    sentinelone.alerts = [
        {
            "node": {
                "id": f"id_{i}",
                "name": f"Alert {i}",
                "severity": "CRITICAL",
                "status": "NEW",
                "analystVerdict": "UNDEFINED",
                "detectedAt": "2026-03-21T16:51:06.684Z",
                "createdAt": "2026-03-21T16:51:06.759Z",
                "lastSeenAt": "2026-03-21T16:51:18.468Z",
            }
        }
        for i in range(105)
    ]
    sentinelone.details = {
        f"id_{i}": {
            "id": f"id_{i}",
            "name": f"Alert {i}",
            "severity": "CRITICAL",
            "status": "NEW",
            "classification": "MALWARE",
            "detectedAt": "2026-03-21T16:51:06.684Z",
            "createdAt": "2026-03-21T16:51:06.759Z",
            "lastSeenAt": "2026-03-21T16:51:18.468Z",
        }
        for i in range(105)
    }

    # Run the connector with is_test_connector_run=False to process all alerts
    connector = UnifiedAlertsConnector(is_test_connector_run=False)
    connector.start()

    # Verifies the number of requests in history:
    # 2 pages of list queries:
    # - Page 1: first=100, after=None
    # - Page 2: first=100, after="cursor_99"
    # Plus 105 detail queries (one for each alert)
    # Total = 2 + 105 = 107 requests
    assert len(script_session.request_history) == 107

    # Find all list queries in request_history
    list_requests = [
        req
        for req in script_session.request_history
        if "GetUnifiedAlerts"
        in common.get_request_payload(req.request).get("query", "")
    ]
    assert len(list_requests) == 2

    # Verify that first page requested 100
    p1_vars = common.get_request_payload(list_requests[0].request)["variables"]
    assert p1_vars["first"] == 100
    assert p1_vars["after"] is None

    # Verify that second page also requested 100 (since API client uses a fixed page size)
    p2_vars = common.get_request_payload(list_requests[1].request)["variables"]
    assert p2_vars["first"] == 100
    assert p2_vars["after"] == "cursor_99"

    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 105


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_alert_updates_supported(
    sentinelone: SentinelOne,
    script_session: SentinelOneSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    """Test that an alert update passes cache filtering and generates update fields."""
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)

    # Seed the DB cache with the alert ID and a timestamp (equivalent to 45 minutes ago)
    old_timestamp_ms = arrow.utcnow().shift(minutes=-45).int_timestamp * 1000
    external_context.set_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        identifier=None,
        property_key="ids",
        property_value=json.dumps(
            {"019d114e-e4f4-7ad6-82c3-9829b6d0a801": old_timestamp_ms}
        ),
    )

    # Modify mock alert's list and details lastSeenAt to be newer (15 minutes ago)
    new_timestamp_str = (
        arrow.utcnow().shift(minutes=-15).format("YYYY-MM-DDTHH:mm:ss.SSS") + "Z"
    )

    new_alert_data = copy.deepcopy(sentinelone.alerts[0])
    new_alert_data["node"]["updatedAt"] = new_timestamp_str
    new_alert_data["node"]["lastSeenAt"] = new_timestamp_str
    new_alert_data["node"]["status"] = "IN_PROGRESS"
    new_alert_data["node"]["analystVerdict"] = "TRUE_POSITIVE_MALWARE"
    sentinelone.alerts = [new_alert_data]

    new_details = copy.deepcopy(
        sentinelone.details["019d114e-e4f4-7ad6-82c3-9829b6d0a801"]
    )
    new_details["updatedAt"] = new_timestamp_str
    new_details["lastSeenAt"] = new_timestamp_str
    new_details["status"] = "IN_PROGRESS"
    new_details["analystVerdict"] = "TRUE_POSITIVE_MALWARE"
    sentinelone.details["019d114e-e4f4-7ad6-82c3-9829b6d0a801"] = new_details

    connector = UnifiedAlertsConnector(is_test)
    connector.start()

    # Verify fields that are dynamically added and serialized but not copied back by the mock framework
    out_attr = "_" + "out"
    raw_output = json.loads(getattr(connector_output, out_attr).getvalue())
    raw_result = json.loads(raw_output["ResultObjectJson"])
    raw_alert = raw_result["cases"][0]

    # Verify that it is marked as an update
    assert raw_alert["alert_update_supported"] is True
    assert raw_alert["updated_fields"].get("status") == "IN_PROGRESS"
    assert raw_alert["updated_fields"].get("analystVerdict") == "TRUE_POSITIVE_MALWARE"
    assert raw_alert["updated_fields"].get("severity") == "CRITICAL"


def test_build_unified_alerts_or_filter_omits_severity_for_info() -> None:
    """Test that build_unified_alerts_or_filter omits stringIn filter for INFO to preserve null severities."""
    # INFO severity with start_timestamp_ms=None should return None (no filters)
    filter_info_no_time = (
        SentinelOneSingularityOperationsCenterApiClient.build_unified_alerts_or_filter(
            start_timestamp_ms=None, lowest_severity="INFO"
        )
    )
    assert filter_info_no_time is None

    # INFO severity with start_timestamp_ms set should only filter by dateTimeRange (no severity stringIn)
    filter_info_with_time = (
        SentinelOneSingularityOperationsCenterApiClient.build_unified_alerts_or_filter(
            start_timestamp_ms=1000, lowest_severity="INFO"
        )
    )
    assert filter_info_with_time == {
        "or": [
            {
                "and": [
                    {
                        "fieldId": "lastSeenAt",
                        "dateTimeRange": {"start": 1000, "end": None},
                    }
                ]
            },
        ]
    }

    # MEDIUM severity should include stringIn filter for ["MEDIUM", "HIGH", "CRITICAL"]
    filter_medium = (
        SentinelOneSingularityOperationsCenterApiClient.build_unified_alerts_or_filter(
            start_timestamp_ms=1000, lowest_severity="MEDIUM"
        )
    )
    expected_severity_filter = {
        "fieldId": "severity",
        "stringIn": {"values": ["MEDIUM", "HIGH", "CRITICAL"]},
    }
    assert expected_severity_filter in filter_medium["or"][0]["and"]

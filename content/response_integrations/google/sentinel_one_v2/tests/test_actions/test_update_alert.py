from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from sentinel_one_v2.actions import UpdateAlert
from sentinel_one_v2.core.constants import PRODUCT_NAME, SELECT_ONE
from sentinel_one_v2.tests.common import (
    TEST_ALERT_ID,
    get_endpoint_list,
    MOCK_CLOUD_ALERT,
)
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

BASE_ACTION_PARAMETERS: dict[str, str] = {
    "Alert ID": TEST_ALERT_ID,
    "Status": SELECT_ONE,
    "Verdict": SELECT_ONE,
}

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully updated alert {TEST_ALERT_ID} in {PRODUCT_NAME}."
)

NOT_FOUND_MSG: str = (
    f"alert with ID {TEST_ALERT_ID} wasn’t found in SentinelOne. "
    f"Please check the spelling."
)

INVALID_ID_MSG: str = 'parameter "Alert ID" is not Valid'

TEST_INVALID_ALERT_ID: str = "invalid-id"


@set_metadata(
    parameters={
        "Alert ID": TEST_ALERT_ID,
        "Status": "Resolved",
        "Verdict": "True Positive",
    },
    integration_config=INTEGRATION_CONFIG,
)
def test_update_status_and_verdict_success(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput
) -> None:
    """Test successfully updating both status and verdict."""
    sentinel_one_v2.add_cloud_detection_alert(TEST_ALERT_ID, MOCK_CLOUD_ALERT)
    UpdateAlert.main()

    accessed_endpoints: list[str] = get_endpoint_list(script_session.request_history)
    alert = sentinel_one_v2.get_cloud_detection_alert(TEST_ALERT_ID)

    assert accessed_endpoints == [
        "/web/api/v2.1/agents/count",
        "/web/api/v2.1/cloud-detection/alerts",
        "/web/api/v2.1/cloud-detection/alerts/incident",
        "/web/api/v2.1/cloud-detection/alerts/analyst-verdict",
        "/web/api/v2.1/cloud-detection/alerts",
    ]
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert alert.incident_status == "resolved"
    assert alert.verdict == "true_positive"
    assert len(script_session.request_history) == 5


@set_metadata(
    parameters={
        "Alert ID": "12345",
        "Status": "Resolved",
        "Verdict": "True Positive",
    },
    integration_config=INTEGRATION_CONFIG,
)
def test_invalid_alert_id_fail(
    action_output: MockActionOutput,
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,  # pylint: disable=unused-argument
) -> None:
    """Test failure when an invalid alert ID is provided."""
    UpdateAlert.main()
    assert len(script_session.request_history) == 2
    assert action_output.results.result_value is False
    assert "alert with ID 12345 wasn’t found" in action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    parameters={
        "Alert ID": TEST_INVALID_ALERT_ID,
        "Status": "Resolved",
        "Verdict": "True Positive",
    },
    integration_config=INTEGRATION_CONFIG,
)
def test_invalid_alert_id_format_fail(
    action_output: MockActionOutput,
) -> None:
    """Test failure when an invalid format alert ID is provided."""
    UpdateAlert.main()
    assert action_output.results.result_value is False
    assert INVALID_ID_MSG in action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    parameters={
        "Alert ID": TEST_ALERT_ID,
        "Status": SELECT_ONE,
        "Verdict": "True Positive",
    },
    integration_config=INTEGRATION_CONFIG,
)
def test_update_verdict_success(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    """Test successfully updating only the verdict."""
    sentinel_one_v2.add_cloud_detection_alert(TEST_ALERT_ID, MOCK_CLOUD_ALERT)
    UpdateAlert.main()

    accessed_endpoints: list[str] = get_endpoint_list(script_session.request_history)
    alert = sentinel_one_v2.get_cloud_detection_alert(TEST_ALERT_ID)

    assert accessed_endpoints[-2:] == [
        "/web/api/v2.1/cloud-detection/alerts/analyst-verdict",
        "/web/api/v2.1/cloud-detection/alerts",
    ]
    assert action_output.results.result_value is True
    assert alert.verdict == "true_positive"

from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from proofpoint_threat_protection.actions import ping

from proofpoint_threat_protection.tests import common
from proofpoint_threat_protection.tests.core.product import (
    ProofpointThreatProtection,
)
from proofpoint_threat_protection.tests.core.session import (
    ProofpointThreatProtectionSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PING_SUCCESS_MESSAGE: str = (
    "Successfully connected to the Proofpoint Threat Protection server with the "
    "provided connection parameters!"
)
PING_FAIL_MESSAGE: str = (
    "Failed to connect to the Proofpoint Threat Protection server!\n"
    'Reason: 400: {"error": {"message": "Failed to authenticate to Proofpoint '
    'Cloud Threat Response", "errors": [{"errorMessage": "Wrong '
    'Credentials!"}]}}'
)


@set_metadata(integration_config=common.CONFIG)
def test_ping_success(
    proofpoint_ctr: ProofpointThreatProtection,
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
) -> None:
    """Test for successful ping action"""
    proofpoint_ctr.cleanup_allow_list_entries()
    proofpoint_ctr.add_allow_list_entries(common.ALLOW_LIST_ENTRIES_JSON["entries"])
    ping.main()
    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=PING_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


FAILED_CONFIG = common.CONFIG.copy()
FAILED_CONFIG["Client Secret"] = "invalid client secret"


@set_metadata(integration_config=FAILED_CONFIG)
def test_ping_fail(
    script_session: ProofpointThreatProtectionSession,
    action_output: MockActionOutput,
) -> None:
    """Test for failed ping action"""
    ping.main()
    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=PING_FAIL_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )

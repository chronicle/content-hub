from __future__ import annotations

import json

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import download_remediation_log
from rubrik_security_cloud.tests.common import (
    CONFIG_PATH,
    DSPM_VIOLATION_ID,
    MOCK_CREATE_VIOLATION_REMEDIATION,
    MOCK_DSPM_VIOLATION_DETAILS,
    OBJECT_ID,
    OBJECT_NAME,
)
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

DEFAULT_PARAMETERS = {"Object ID": OBJECT_ID, "Violation ID": DSPM_VIOLATION_ID}
TARGET_FILE_NAME = f"{OBJECT_NAME} actions log"
LOG_FILE_NAME = f"{TARGET_FILE_NAME}.csv"
POLLING_PARAMETERS = {
    **DEFAULT_PARAMETERS,
    "additional_data": json.dumps({"target_file_name": TARGET_FILE_NAME, "started_at": "2026-01-01T00:00:00+00:00"}),
}


class TestDownloadRemediationLog:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_download_remediation_log_trigger(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.dspm_violation_details_response = MOCK_DSPM_VIOLATION_DETAILS
        rubrik.create_violation_remediation_response = MOCK_CREATE_VIOLATION_REMEDIATION

        download_remediation_log.main(is_first_run=True)

        assert "Waiting for RSC to list" in action_output.results.output_message
        assert action_output.results.execution_state.value == 1
        action_context = json.loads(action_output.results.result_value)
        assert action_context["target_file_name"] == TARGET_FILE_NAME
        assert action_context["started_at"]

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=POLLING_PARAMETERS)
    def test_download_remediation_log_ready(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.user_files = [
            {
                "externalId": "test-external-id",
                "filename": LOG_FILE_NAME,
                "type": "REMEDIATION_ACTIONS_LOG_CSV",
                "state": "READY",
                "createdAt": "2026-01-01T00:05:00.000Z",
            }
        ]
        rubrik.file_download_content = "action,status\nquarantine,success\n"

        download_remediation_log.main(is_first_run=False)

        download_requests = [
            req
            for req in script_session.request_history
            if req.request.url.path.endswith("/file-downloads/test-external-id")
        ]
        assert len(download_requests) == 1

        assert f"Remediation log '{LOG_FILE_NAME}' attached to case" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=POLLING_PARAMETERS)
    def test_download_remediation_log_generation_failed(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.user_files = [
            {
                "externalId": "test-external-id",
                "filename": LOG_FILE_NAME,
                "type": "REMEDIATION_ACTIONS_LOG_CSV",
                "state": "FAILED",
                "createdAt": "2026-01-01T00:05:00.000Z",
            }
        ]

        download_remediation_log.main(is_first_run=False)

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={**DEFAULT_PARAMETERS, "Object ID": "55555555-5555-4555-8555-555555555555"},
    )
    def test_download_remediation_log_object_mismatch(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.dspm_violation_details_response = MOCK_DSPM_VIOLATION_DETAILS

        download_remediation_log.main(is_first_run=True)

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2

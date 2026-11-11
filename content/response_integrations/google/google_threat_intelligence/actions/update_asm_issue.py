from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    INTEGRATION_DISPLAY_NAME,
    ISSUE_STATUS_MAPPING,
    UPDATE_ASM_ISSUE_SCRIPT_NAME,
)
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from TIPCommon.extraction import extract_action_param

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {UPDATE_ASM_ISSUE_SCRIPT_NAME}."


class UpdateASMIssue(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = []

    def _extract_action_parameters(self) -> None:
        self.params.issue_id = extract_action_param(
            self.soar_action,
            param_name="Issue ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.issue_status = extract_action_param(
            self.soar_action,
            param_name="Status",
            is_mandatory=True,
            print_value=True,
        )
        self.params.issue_status = ISSUE_STATUS_MAPPING.get(self.params.issue_status)

    def _validate_params(self) -> None:
        if self.params.issue_status is None:
            raise GoogleThreatIntelligenceExceptions(
                '"Status" parameter should have a value.'
            )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        result = self.api_client.update_issue(
            issue_id=self.params.issue_id,
            status=self.params.issue_status,
        )

        self.output_message = (
            f"Successfully updated the issue with the ID '{self.params.issue_id}' "
            f"in {INTEGRATION_DISPLAY_NAME}."
        )
        self.json_results = result


def main() -> None:
    UpdateASMIssue(UPDATE_ASM_ISSUE_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

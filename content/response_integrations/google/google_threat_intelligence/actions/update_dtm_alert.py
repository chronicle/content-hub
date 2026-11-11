from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    ALERT_STATUS_MAPPING,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_DTM_ALERT_SCRIPT_NAME,
)
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from TIPCommon.extraction import extract_action_param

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {UPDATE_DTM_ALERT_SCRIPT_NAME}."


class UpdateDTMAlert(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.alert_id = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.alert_status = extract_action_param(
            self.soar_action,
            param_name="Status",
            print_value=True,
        )
        self.params.alert_status = ALERT_STATUS_MAPPING.get(self.params.alert_status)

    def _validate_params(self) -> None:
        if self.params.alert_status is None:
            raise GoogleThreatIntelligenceExceptions(
                '"Status" parameter should have a value.'
            )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        alert = self.api_client.update_alert(
            self.params.alert_id.lower(),
            self.params.alert_status,
        )

        self.output_message = (
            f"Successfully updated alert with ID {self.params.alert_id} in "
            f"{INTEGRATION_DISPLAY_NAME}."
        )

        self.logger.info("Adding alert to JSON results")
        self.json_results = alert.raw_data


def main() -> None:
    UpdateDTMAlert(UPDATE_DTM_ALERT_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

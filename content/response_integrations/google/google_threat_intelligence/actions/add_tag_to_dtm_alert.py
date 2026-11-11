from __future__ import annotations

from TIPCommon import validation
from TIPCommon.extraction import extract_action_param
from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import ADD_TAG_TO_DTM_ALERT_SCRIPT_NAME


MODE_OPTIONS = ["Append", "Set"]

SUCCESS_MESSAGE = (
    "Successfully updated the alert with "
    "the ID {alert_id} in Google Threat Intelligence"
)
ERROR_MESSAGE = f"Error executing action {ADD_TAG_TO_DTM_ALERT_SCRIPT_NAME}."


class AddTagToDtmAlert(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = ERROR_MESSAGE
        self.is_success = True

    def _extract_action_parameters(self) -> None:
        self.params.alert_id = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.tags = extract_action_param(
            self.soar_action,
            param_name="Tags",
            is_mandatory=True,
            print_value=True,
        )
        self.params.mode = extract_action_param(
            self.soar_action,
            param_name="Mode",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        self.params.tags = validator.validate_csv(
            param_name="Tags",
            csv_string=self.params.tags,
            print_value=False,
        )

        self.params.mode = validator.validate_ddl(
            param_name="Mode",
            value=self.params.mode,
            ddl_values=MODE_OPTIONS,
        )

    def _perform_action(self, _=None) -> bool:
        self.api_client.test_connectivity()

        append_enabled = self.params.mode == "Append"
        result = self.api_client.update_dtm_alert_tags(
            self.params.alert_id, self.params.tags, append=append_enabled
        )

        self.logger.info(f"Result: {result}")

        if result:
            self.output_message = SUCCESS_MESSAGE.format(alert_id=self.params.alert_id)

        return True


def main() -> None:
    AddTagToDtmAlert(ADD_TAG_TO_DTM_ALERT_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

from __future__ import annotations

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    INTEGRATION_DISPLAY_NAME,
    SET_DTM_ALERT_ANALYSIS_SCRIPT_NAME,
)
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from google_threat_intelligence.core.utils import verify_paths_accessibility


class SetDTMAnalysis(BaseAction):
    def _extract_action_parameters(self) -> None:
        self.params.alert_id = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.text = extract_action_param(
            self.soar_action,
            param_name="Text",
            is_mandatory=True,
            print_value=True,
        )
        self.params.attachment_file_paths = extract_action_param(
            self.soar_action,
            param_name="Attachment File Paths",
            remove_whitespaces=False,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)

        self.params.attachment_file_paths = validator.validate_csv(
            param_name="Attachment File Paths",
            csv_string=self.params.attachment_file_paths,
            print_value=True,
        )

        verify_paths_accessibility(self.params.attachment_file_paths, self.logger)

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()

        self.api_client.update_analysis_text_on_alert(
            alert_id=self.params.alert_id,
            text=self.params.text,
        )

        try:
            self.api_client.upload_file_to_alerts_analysis(
                alert_id=self.params.alert_id,
                file_paths=self.params.attachment_file_paths,
            )
        except GoogleThreatIntelligenceExceptions as e:
            raise type(e)(
                "Attachments upload failed. "
                f"The Alert may not have been saved correctly. {e}"
            ) from e

        self.output_message = (
            f"Successfully updated the alert with the ID '{self.params.alert_id}' "
            f"in {INTEGRATION_DISPLAY_NAME}."
        )


def main() -> None:
    SetDTMAnalysis(SET_DTM_ALERT_ANALYSIS_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

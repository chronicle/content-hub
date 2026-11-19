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

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from ..core.base_action import BaseAction
from ..core.constants import (
    INTEGRATION_DISPLAY_NAME,
    SET_DTM_ALERT_ANALYSIS_SCRIPT_NAME,
)
from ..core.exceptions import GoogleThreatIntelligenceExceptions
from ..core.utils import verify_paths_accessibility


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

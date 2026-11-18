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
from ..core.base_action import BaseAction
from ..core.constants import (
    ADD_ASM_ISSUE_NOTE_SCRIPT_NAME,
    ASMItemType,
)


SUCCESS_MESSAGE = (
    "Successfully updated the alert with "
    "the ID {alert_id} in Google Threat Intelligence"
)
ERROR_MESSAGE = f"Error executing action {ADD_ASM_ISSUE_NOTE_SCRIPT_NAME}."


class AddAsmIssueNote(BaseAction):
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
        self.params.text = extract_action_param(
            self.soar_action,
            param_name="Text",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, _=None) -> bool:
        self.api_client.test_connectivity()
        self.api_client.set_project_id(self.api_client.asm_project_name)
        self.logger.info(f"ASM Project Name: {self.api_client.asm_project_name}")
        self.logger.info(f"ASM Project ID: {self.api_client.project_id}")
        result = self.api_client.add_asm_note(
            ASMItemType.ISSUE, self.params.alert_id, self.params.text
        )
        self.logger.info(f"Result: {result}")
        self.is_success = result.get("success", False)

        if self.is_success:
            self.output_message = SUCCESS_MESSAGE.format(alert_id=self.params.alert_id)

        return True


def main() -> None:
    AddAsmIssueNote(ADD_ASM_ISSUE_NOTE_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

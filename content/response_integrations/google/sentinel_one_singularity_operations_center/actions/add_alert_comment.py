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

from ..core.base_action import SentinelOneSingularityOperationsCenterAction
from ..core.exceptions import SentinelOneSingularityOperationsCenterError

# Mapping from UI Dropdowns to SentinelOne API Enum Values
COMMENT_TYPE_MAP = {"Plain Text": "PLAIN_TEXT", "Markdown": "MARKDOWN"}


class AddAlertComment(SentinelOneSingularityOperationsCenterAction):
    def __init__(self) -> None:
        super().__init__("SentinelOneSingularityOperationsCenter - Add Alert Comment")
        self.output_message: str = ""
        self.result_value: bool = False

    def _perform_action(self, _current_entity: None = None) -> None:
        alert_id = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            is_mandatory=True,
            input_type=str,
        )
        comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            is_mandatory=True,
            input_type=str,
        )
        comment_type_input = extract_action_param(
            self.soar_action,
            param_name="Comment Type",
            is_mandatory=False,
            input_type=str,
        )

        # Map UI parameter selections to GraphQL enum values
        comment_type = (
            COMMENT_TYPE_MAP.get(comment_type_input, "PLAIN_TEXT")
            if comment_type_input
            else "PLAIN_TEXT"
        )

        self.logger.info(f"Adding comment to SentinelOne alert {alert_id}...")

        try:
            note = self.api_client.add_alert_comment(
                alert_id=alert_id,
                comment=comment,
                comment_type=comment_type,
            )
        except SentinelOneSingularityOperationsCenterError as e:
            err_msg = str(e)
            if (
                "could not be parsed into a UUID" in err_msg
                or "invalid uuid" in err_msg.lower()
                or "not found" in err_msg.lower()
            ):
                raise SentinelOneSingularityOperationsCenterError(
                    f"alert with ID {alert_id} wasn't found in SentinelOne Singularity Operations Center. Please check the spelling."
                ) from e
            raise SentinelOneSingularityOperationsCenterError(err_msg) from e

        if note.id:
            self.output_message = (
                f"Successfully added comment to SentinelOne alert '{alert_id}'."
            )
            self.result_value = True
        else:
            raise SentinelOneSingularityOperationsCenterError(
                f'Error executing action "Add Alert Comment". Reason: No response data received for alert {alert_id}.'
            )


def main() -> None:
    """Run the AddAlertComment action."""
    AddAlertComment().run()


if __name__ == "__main__":
    main()

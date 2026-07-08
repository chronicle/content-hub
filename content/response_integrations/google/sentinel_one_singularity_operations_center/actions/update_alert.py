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
from ..core.constants import STATUS_MAP, VERDICT_MAP
from ..core.exceptions import (
    SentinelOneSingularityOperationsCenterError,
    UserNotFoundError,
)


class UpdateAlert(SentinelOneSingularityOperationsCenterAction):
    def __init__(self) -> None:
        super().__init__("SentinelOneSingularityOperationsCenter - Update Alert")
        self.output_message: str = ""
        self.result_value: bool = False

    def _perform_action(self, current_entity: None = None) -> None:  # noqa: ARG002, C901, PLR0912
        alert_id = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            is_mandatory=True,
            input_type=str,
        )
        status_input = extract_action_param(
            self.soar_action,
            param_name="Status",
            is_mandatory=False,
            input_type=str,
        )
        verdict_input = extract_action_param(
            self.soar_action,
            param_name="Verdict",
            is_mandatory=False,
            input_type=str,
        )
        assignee_input = extract_action_param(
            self.soar_action,
            param_name="Assignee",
            is_mandatory=False,
            input_type=str,
        )

        # Validate that at least one update parameter is provided
        if not any([status_input, verdict_input, assignee_input]):
            self.output_message = (
                "Failed to update alert: At least one update parameter "
                "('Status', 'Verdict', or 'Assignee') must be provided."
            )
            self.result_value = False
            return

        # Map UI parameter selections to GraphQL enum values
        status_api = STATUS_MAP.get(status_input) if status_input else None
        verdict_api = VERDICT_MAP.get(verdict_input) if verdict_input else None

        # Parse the Assignee parameter to assignee_id (False means not provided, None means unassign, int is User ID)
        assignee_id: int | bool | None = False
        if assignee_input:
            assignee_stripped = assignee_input.strip()
            if assignee_stripped.lower() == "unassign":
                assignee_id = None
            elif "@" in assignee_stripped:  # Email resolution path
                self.logger.info(
                    f"Resolving SentinelOne User ID for email '{assignee_stripped}'..."
                )
                try:
                    assignee_id = self.api_client.get_user_id_by_email(
                        assignee_stripped
                    )
                    self.logger.info(
                        f"Successfully resolved email '{assignee_stripped}' to User ID {assignee_id}."
                    )
                except UserNotFoundError as e:
                    self.output_message = f"Failed to update alert: {e}"
                    self.result_value = False
                    return
            else:  # Direct ID path (fallback)
                try:
                    assignee_id = int(assignee_stripped)
                except ValueError:
                    self.output_message = (
                        "Failed to update alert: Assignee parameter must be an email address, "
                        "a numerical User ID, or 'Unassign' to remove assignment."
                    )
                    self.result_value = False
                    return

        self.logger.info(f"Updating SentinelOne alert {alert_id}...")

        try:
            result = self.api_client.update_alert(
                alert_id=alert_id,
                status=status_api,
                analyst_verdict=verdict_api,
                assignee_id=assignee_id,
            )
        except SentinelOneSingularityOperationsCenterError as e:
            self.output_message = str(e)
            self.result_value = False
            return

        if result.is_scheduled:
            self.output_message = (
                f"Alert update request was accepted and scheduled for background execution. "
                f"Execution ID: '{result.execution_id}'."
            )
            self.result_value = True
        elif result.is_skipped:
            self.output_message = f"Action was skipped for alert '{alert_id}'. Reasons: {', '.join(result.skips)}"
            self.result_value = False
        else:
            updates = []
            if status_input:
                updates.append(f"Status to '{status_input}'")
            if verdict_input:
                updates.append(f"Verdict to '{verdict_input}'")
            if assignee_input:
                updates.append(f"Assignee to '{assignee_input}'")

            self.output_message = f"Successfully updated SentinelOne alert '{alert_id}': {', '.join(updates)}."
            self.result_value = True


def main() -> None:
    """Run the UpdateAlert action."""
    UpdateAlert().run()


if __name__ == "__main__":
    main()

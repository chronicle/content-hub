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

    def _resolve_assignee_id(self, assignee_input: str) -> int | None | bool:
        """Parse Assignee parameter into API assignee_id.

        Returns:
            int: User ID for assignment.
            None: Unassign alert.
            bool (False): Resolution failed (error message set in self.output_message).
        """
        assignee_stripped = assignee_input.strip()
        if assignee_stripped.lower() == "unassign":
            return None

        if "@" in assignee_stripped:
            self.logger.info("Resolving SentinelOne User ID for assignee email...")
            try:
                user_id = self.api_client.get_user_id_by_email(assignee_stripped)
                self.logger.info(f"Successfully resolved email to User ID {user_id}.")
                return user_id
            except UserNotFoundError as e:
                self.output_message = f"Failed to update alert: {e}"
                return False

        try:
            return int(assignee_stripped)
        except ValueError:
            self.output_message = (
                "Failed to update alert: Assignee parameter must be an email address, "
                "a numerical User ID, or 'Unassign' to remove assignment."
            )
            return False

    def _perform_action(self, _current_entity: None = None) -> None:
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

        if not any([status_input, verdict_input, assignee_input]):
            self.output_message = (
                "Failed to update alert: At least one update parameter "
                "('Status', 'Verdict', or 'Assignee') must be provided."
            )
            self.result_value = False
            return

        status_api = STATUS_MAP.get(status_input) if status_input else None
        verdict_api = VERDICT_MAP.get(verdict_input) if verdict_input else None

        assignee_id: int | None | bool = False
        if assignee_input:
            assignee_id = self._resolve_assignee_id(assignee_input)
            if assignee_id is False:
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
            self.output_message = (
                f"Action was skipped for alert '{alert_id}'. "
                f"Reasons: {', '.join(result.skips)}"
            )
            self.result_value = False
        else:
            updates = []
            if status_input:
                updates.append(f"Status to '{status_input}'")
            if verdict_input:
                updates.append(f"Verdict to '{verdict_input}'")
            if assignee_input:
                updates.append(f"Assignee to '{assignee_input}'")

            self.output_message = (
                f"Successfully updated SentinelOne alert '{alert_id}': "
                f"{', '.join(updates)}."
            )
            self.result_value = True


def main() -> None:
    """Run the UpdateAlert action."""
    UpdateAlert().run()


if __name__ == "__main__":
    main()

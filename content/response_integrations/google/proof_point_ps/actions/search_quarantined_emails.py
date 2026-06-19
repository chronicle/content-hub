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

from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param

from ..core.api_utils import calculate_time_range
from ..core.base_action import BaseProofPointPSAction
from ..core.constants import SEARCH_ACTION_NAME, TIME_FORMAT

if TYPE_CHECKING:
    from typing import Never


DLP_VIOLATION_MAPPING = {
    "No": None,
    "Basic": "t",
    "Detailed": "details",
}


class SearchQuarantinedEmails(BaseProofPointPSAction):
    """Search Quarantined Emails action."""

    def __init__(self) -> None:
        super().__init__(SEARCH_ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        """Extracts all action-specific parameters."""
        self.params.guid = extract_action_param(
            self.soar_action, param_name="Message GUID", print_value=True
        )
        self.params.msgid = extract_action_param(
            self.soar_action, param_name="Message ID", print_value=True
        )
        self.params.sender = extract_action_param(
            self.soar_action, param_name="Sender", print_value=True
        )
        self.params.recipient = extract_action_param(
            self.soar_action, param_name="Recipient", print_value=True
        )
        self.params.subject = extract_action_param(
            self.soar_action, param_name="Subject", print_value=True
        )
        self.params.time_frame = extract_action_param(
            self.soar_action, param_name="Time Frame", print_value=True
        )
        self.params.start_time = extract_action_param(
            self.soar_action, param_name="Start Time", print_value=True
        )
        self.params.end_time = extract_action_param(
            self.soar_action, param_name="End Time", print_value=True
        )
        self.params.folder = extract_action_param(
            self.soar_action, param_name="Folder Name", print_value=True
        )
        self.params.queryid = extract_action_param(
            self.soar_action, param_name="Query ID", print_value=True
        )
        dlp_violation_raw = extract_action_param(
            self.soar_action, param_name="Fetch DLP Violation", print_value=True
        )
        self.params.dlpviolation = DLP_VIOLATION_MAPPING.get(dlp_violation_raw)
        status_bool = extract_action_param(
            self.soar_action,
            param_name="Fetch Message Status",
            input_type=bool,
            print_value=True,
        )
        self.params.messagestatus = "t" if status_bool else None
        self.params.limit = extract_action_param(
            self.soar_action,
            param_name="Max Results To Return",
            input_type=int,
            print_value=True,
        )

    def _perform_action(self, _: Never) -> None:
        """Execute the smart search operation.

        Args:
            _: Never input.

        """
        start_dt, end_dt = calculate_time_range(
            time_frame=self.params.time_frame,
            start_time_str=self.params.start_time,
            end_time_str=self.params.end_time,
        )
        start_date = start_dt.strftime(TIME_FORMAT)
        end_date = end_dt.strftime(TIME_FORMAT)

        sender = self.params.sender or "*"

        records = self.api_client.search(
            sender=sender,
            recipient=self.params.recipient,
            subject=self.params.subject,
            start_date=start_date,
            end_date=end_date,
            folder=self.params.folder,
            msgid=self.params.msgid,
            queryid=self.params.queryid,
            dlpviolation=self.params.dlpviolation,
            messagestatus=self.params.messagestatus,
            limit=self.params.limit,
        )

        if self.params.guid:
            guid_lower = self.params.guid.lower()
            records = [
                r for r in records
                if guid_lower in {
                    r.guid.lower() if r.guid else "",
                    r.localguid.lower() if r.localguid else "",
                }
            ]

        if records:
            self.json_results = [r.to_json() for r in records]
            self.result_value = True
            self.output_message = (
                f"Successfully found {len(records)} quarantined emails."
            )
        else:
            self.json_results = []
            self.output_message = (
                "No quarantined emails were found matching the criteria."
            )
            self.result_value = False


def main() -> None:
    SearchQuarantinedEmails().run()


if __name__ == "__main__":
    main()

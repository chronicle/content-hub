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
from TIPCommon.transformation import string_to_multi_value

from ..core.api_utils import calculate_time_range
from ..core.base_action import BaseProofPointPSAction
from ..core.constants import MOVE_ACTION_NAME, TIME_FORMAT
from ..core.exceptions import InvalidParameterError

if TYPE_CHECKING:
    from typing import Never


class MoveQuarantinedEmail(BaseProofPointPSAction):
    """Move Quarantined Email action."""

    def __init__(self) -> None:
        super().__init__(MOVE_ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        """Extracts action-specific parameters."""
        self.params.guid_input = extract_action_param(
            self.soar_action,
            param_name="Message GUIDs",
            is_mandatory=True,
            print_value=True,
        )
        self.params.time_frame = extract_action_param(
            self.soar_action,
            param_name="Time Frame",
            is_mandatory=False,
            default_value="Last Hour",
            print_value=True,
        )
        self.params.start_time = extract_action_param(
            self.soar_action,
            param_name="Start Time",
            is_mandatory=False,
            print_value=True,
        )
        self.params.end_time = extract_action_param(
            self.soar_action,
            param_name="End Time",
            is_mandatory=False,
            print_value=True,
        )
        self.params.folder = extract_action_param(
            self.soar_action,
            param_name="Folder Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.target_folder = extract_action_param(
            self.soar_action,
            param_name="Target Folder Name",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, _: Never) -> None:
        """Execute the move operation.

        Args:
            _: Never input.

        """
        if self.params.time_frame == "Custom" and not self.params.start_time:
            msg = "Start Time is required when Time Frame is set to 'Custom'."
            raise InvalidParameterError(
                msg
            )
        if self.params.time_frame != "Custom" and (
            self.params.start_time or self.params.end_time
        ):
            msg = (
                "Start Time or End Time can only be provided when 'Custom' is "
                "selected for the Time Frame parameter."
            )
            raise InvalidParameterError(
                msg
            )

        guids = string_to_multi_value(self.params.guid_input)
        successful_guids = []
        failed_guids = []

        try:
            start_dt, end_dt = calculate_time_range(
                time_frame=self.params.time_frame,
                start_time_str=self.params.start_time,
                end_time_str=self.params.end_time,
            )
            start_date = start_dt.strftime(TIME_FORMAT)
            end_date = end_dt.strftime(TIME_FORMAT)

            records = self.api_client.search(
                sender="*",
                folder=self.params.folder,
                start_date=start_date,
                end_date=end_date,
            )
            valid_guids = set()
            for r in records:
                if r.guid:
                    valid_guids.add(r.guid.lower().strip())
                if r.localguid:
                    valid_guids.add(r.localguid.lower().strip())
        except Exception as e:
            valid_guids = None
            self.soar_action.LOGGER.exception(
                "Failed to pre-validate GUIDs via search API: %s", e
            )

        for guid in guids:
            if valid_guids is not None and guid.lower() not in valid_guids:
                failed_guids.append((guid, "Message not found"))
                continue

            try:
                self.api_client.execute_quarantine_action(
                    action="move",
                    folder=self.params.folder,
                    localguid=guid,
                    targetfolder=self.params.target_folder,
                )
                successful_guids.append(guid)
            except Exception as e:
                failed_guids.append((guid, str(e)))

        if not successful_guids:
            msg = (
                f"Failed to move any quarantined emails. Errors: "
                f"{'; '.join(f'{g}: {err}' for g, err in failed_guids)}"
            )
            raise Exception(
                msg
            )

        if failed_guids:
            self.result_value = False
            output_msg = "Failed to move some quarantined emails."
            if successful_guids:
                output_msg += (
                    f" Successfully moved: {', '.join(successful_guids)} "
                    f"to {self.params.target_folder}."
                )
            output_msg += f" Failed for: {', '.join(f'{g} (Error: {err})' for g, err in failed_guids)}"
            self.output_message = output_msg
            return

        self.result_value = True
        self.output_message = (
            f"Successfully moved quarantined email(s): "
            f"{', '.join(successful_guids)} to {self.params.target_folder}."
        )


def main() -> None:
    MoveQuarantinedEmail().run()


if __name__ == "__main__":
    main()

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


from ..core.base_action import BaseProofPointPSAction
from ..core.constants import RESUBMIT_ACTION_NAME
from ..core.exceptions import ProofPointPSError

if TYPE_CHECKING:
    from typing import Never


class ResubmitQuarantinedEmail(BaseProofPointPSAction):
    """Resubmit Quarantined Email action."""

    def __init__(self) -> None:
        super().__init__(RESUBMIT_ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        """Extracts action-specific parameters."""
        self.params.guid_input = extract_action_param(
            self.soar_action,
            param_name="Message GUIDs",
            is_mandatory=True,
            print_value=True,
        )

        self.params.folder = extract_action_param(
            self.soar_action,
            param_name="Folder Name",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, _: Never) -> None:
        """Execute the resubmit operation.

        Args:
            _: Never input.

        """
        guids = string_to_multi_value(self.params.guid_input)
        successful_guids = []
        failed_guids = []

        for guid in guids:
            guid_valid = False
            try:
                self.api_client.download_message(guid)
                guid_valid = True
            except Exception:
                guid_valid = False

            if not guid_valid:
                failed_guids.append((guid, "Message not found"))
                continue

            try:
                self.api_client.execute_quarantine_action(
                    action="resubmit",
                    folder=self.params.folder,
                    localguid=guid,
                )
                successful_guids.append(guid)
            except Exception as e:
                failed_guids.append((guid, str(e)))

        if not successful_guids:
            msg = (
                f"Failed to resubmit any quarantined emails. Errors: "
                f"{'; '.join(f'{guid}: {err}' for guid, err in failed_guids)}"
            )
            raise ProofPointPSError(msg)

        if failed_guids:
            self.result_value = False
            output_msg = "Failed to resubmit some quarantined emails."
            if successful_guids:
                output_msg += (
                    f" Successfully resubmitted: {', '.join(successful_guids)}."
                )
            failed_str = ", ".join(
                f"{guid} (Error: {err})" for guid, err in failed_guids
            )
            output_msg += f" Failed for: {failed_str}"
            self.output_message = output_msg
            return

        self.result_value = True
        self.output_message = (
            f"Successfully resubmitted quarantined email(s): "
            f"{', '.join(successful_guids)}"
        )


def main() -> None:
    ResubmitQuarantinedEmail().run()


if __name__ == "__main__":
    main()

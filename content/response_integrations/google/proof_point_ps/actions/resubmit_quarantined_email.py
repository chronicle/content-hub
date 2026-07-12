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
from ..core.exceptions import ProofPointPSError, ProofPointPSHTTPError

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
        folder_name = self.params.folder

        try:
            records = self._validate_folder_and_guids(guids, folder_name)
        except ProofPointPSError as e:
            raise ProofPointPSError(f"Failed to resubmit quarantined email(s). Error: {e}")

        successful_records = []
        successful_guids = []

        records_map = {r.guid: r for r in records if r.guid}
        records_map.update({r.localguid: r for r in records if r.localguid})

        for guid in guids:
            try:
                record = records_map.get(guid)
                self.api_client.execute_quarantine_action(
                    action="resubmit",
                    folder=folder_name,
                    localguid=guid,
                )
                if record:
                    successful_records.append(record.to_json())
                successful_guids.append(guid)
            except ProofPointPSHTTPError as e:
                raise ProofPointPSError(
                    "Failed to resubmit quarantined email(s):"
                    f" GUID {guid} failed during execution. Error: {e}."
                )

        self.json_results = {"success": successful_records}
        self.result_value = True
        self.output_message = (
            f"Successfully resubmitted quarantined email(s): {', '.join(successful_guids)}."
        )



def main() -> None:
    ResubmitQuarantinedEmail().run()


if __name__ == "__main__":
    main()

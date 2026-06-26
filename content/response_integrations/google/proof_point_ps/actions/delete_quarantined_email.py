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
from ..core.constants import DELETE_ACTION_NAME
from ..core.exceptions import ProofPointPSError

if TYPE_CHECKING:
    from typing import Never


class DeleteQuarantinedEmail(BaseProofPointPSAction):
    """Delete Quarantined Email action."""

    def __init__(self) -> None:
        super().__init__(DELETE_ACTION_NAME)

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
        self.params.deleted_folder = extract_action_param(
            self.soar_action, param_name="Deleted Folder Name", print_value=True
        )

    def _perform_action(self, _: Never) -> None:
        """Execute the delete operation.

        Args:
            _: Never input.

        """
        guids = string_to_multi_value(self.params.guid_input)
        successful_records = []
        successful_guids = []
        failed_guids = []

        folder_name = self.params.folder
        deleted_folder = self.params.deleted_folder

        if deleted_folder and folder_name.lower() == deleted_folder.lower():
            self.output_message = "Folder and deleted folder cannot be the same."
            self.result_value = False
            return

        folder_checked = False
        folder_error = None

        for guid in guids:
            try:
                self.api_client.download_message(guid)
                record = self.api_client.get_record_by_guid(guid, folder=folder_name)
                if not record:
                    failed_guids.append(guid)
                    continue
            except ProofPointPSError:
                failed_guids.append(guid)
                continue

            if deleted_folder and not folder_checked:
                try:
                    self._validate_folder(deleted_folder, "Deleted folder")
                except ProofPointPSError:
                    folder_error = f"Deleted folder '{deleted_folder}' does not exist."
                folder_checked = True

            if folder_error:
                continue

            try:
                self.api_client.execute_quarantine_action(
                    action="delete",
                    folder=self.params.folder,
                    localguid=guid,
                    deletedfolder=self.params.deleted_folder,
                )
                successful_records.append(record.to_json())
                successful_guids.append(guid)
            except ProofPointPSError:
                pass

        if folder_error:
            self.json_results = {}
            self.result_value = False
            if failed_guids:
                self.output_message = (
                    "The following message guids were not found in Proofpoint: "
                    f"{', '.join(failed_guids)}. {folder_error}"
                )
            else:
                self.output_message = folder_error
            return

        if successful_guids:
            self.json_results = {
                "success": successful_records
            }
            self.result_value = True
            if failed_guids:
                self.output_message = (
                    f"Successfully deleted quarantined email(s): {', '.join(successful_guids)}. "
                    "The following message guids were not found in Proofpoint: "
                    f"{', '.join(failed_guids)}."
                )
            else:
                self.output_message = (
                    f"Successfully deleted quarantined email(s): {', '.join(successful_guids)}."
                )
        else:
            self.json_results = {}
            self.result_value = False
            if failed_guids:
                self.output_message = (
                    "The following message guids were not found in Proofpoint: "
                    f"{', '.join(failed_guids)}."
                )


def main() -> None:
    DeleteQuarantinedEmail().run()


if __name__ == "__main__":
    main()

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
            self.soar_action,
            param_name="Deleted Folder Name",
            print_value=True
        )

    def _perform_action(self, _: Never) -> None:
        """Execute the delete operation.

        Args:
            _: Never input.

        """
        guids = string_to_multi_value(self.params.guid_input)
        successful_records = []
        successful_guids = []

        folder_name = self.params.folder
        deleted_folder = self.params.deleted_folder

        if deleted_folder and folder_name.lower() == deleted_folder.lower():
            self.output_message = "Folder and deleted folder cannot be the same."
            self.result_value = False
            return

        folder_error = None
        deleted_folder_error = None
        global_missing = []
        folder_missing = []
        records = []
        
        for guid in guids:
            try:
                record = self.api_client.get_record_by_guid(guid, folder=folder_name)
                if not record:
                    folder_missing.append(guid)
                else:
                    records.append(record)
            except ProofPointPSError:
                folder_missing.append(guid)
                folder_error = f"Folder '{folder_name}' does not exist."

            try:
                self.api_client.download_message(guid)
            except ProofPointPSError:
                global_missing.append(guid)
                continue

        failed_guids = list(set(global_missing + folder_missing))
        records_map = {r.guid: r for r in records if r.guid}
        records_map.update({r.localguid: r for r in records if r.localguid})

        for guid in guids:
            if guid in failed_guids:
                continue
            try:
                self.api_client.execute_quarantine_action(
                    action="delete",
                    folder=folder_name,
                    localguid=guid,
                    deletedfolder=deleted_folder,
                )
                record = records_map.get(guid)
                if record:
                    successful_records.append(record.to_json())
                successful_guids.append(guid)
            except ProofPointPSError as e:
                if "deletedfolder" in str(e):
                    deleted_folder_error = (
                        f"Deleted folder '{deleted_folder}' does not exist."
                    )

        if folder_error:
            self.json_results = {}
            self.result_value = False
            self.output_message = folder_error
            return

        error_msgs = []
        if failed_guids:
            error_msgs.append(
                "The following message guids were not found in Proofpoint: "
                f"{', '.join(failed_guids)}."
            )
        if deleted_folder_error:
            error_msgs.append(deleted_folder_error)

        combined_error = " ".join(error_msgs) if error_msgs else None

        if successful_guids:
            self.json_results = {
                "success": successful_records
            }
            self.result_value = True
            if combined_error:
                self.output_message = (
                    f"Successfully deleted quarantined email(s): {', '.join(successful_guids)}. "
                    f"{combined_error}"
                )
            else:
                self.output_message = (
                    f"Successfully deleted quarantined email(s): {', '.join(successful_guids)}."
                )
        else:
            self.json_results = {}
            self.result_value = False
            self.output_message = combined_error


def main() -> None:
    DeleteQuarantinedEmail().run()


if __name__ == "__main__":
    main()

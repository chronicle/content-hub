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
from ..core.constants import RELEASE_ACTION_NAME
from ..core.exceptions import ProofPointPSHTTPError

if TYPE_CHECKING:
    from typing import Never


class ReleaseQuarantinedEmail(BaseProofPointPSAction):
    """Release Quarantined Email action."""

    def __init__(self) -> None:
        super().__init__(RELEASE_ACTION_NAME)

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
        rescan_bool = extract_action_param(
            self.soar_action,
            param_name="Rescan Message",
            input_type=bool,
            print_value=True,
        )
        self.params.scan = "t" if rescan_bool else None
        self.params.brand_template = extract_action_param(
            self.soar_action, param_name="Branding Template", print_value=True
        )
        self.params.security_policy = extract_action_param(
            self.soar_action, param_name="Security Policy", print_value=True
        )

    def _perform_action(self, _: Never) -> None:
        """Execute the release operation.

        Args:
            _: Never input.

        """
        guids = string_to_multi_value(self.params.guid_input)
        successful_records = []
        successful_guids = []
        failed_entries = []
        folder_error = None

        for guid in guids:
            try:
                self.api_client.download_message(guid)
            except ProofPointPSHTTPError:
                failed_entries.append({
                    "guid": guid,
                    "error": "Message not found"
                })
                continue

            folder_name = self.params.folder
            try:
                record = self.api_client.get_record_by_guid(guid, folder=folder_name)
            except ProofPointPSHTTPError as e:
                failed_entries.append({
                    "guid": guid,
                    "error": str(e)
                })
                if "folder" in str(e).lower():
                    folder_error = str(e)
                continue

            if not record:
                err_msg = f"The quarantined email with GUID {guid} does not exist in the '{folder_name}' folder."
                failed_entries.append({
                    "guid": guid,
                    "error": err_msg
                })
                continue

            try:
                self.api_client.execute_quarantine_action(
                    action="release",
                    folder=self.params.folder,
                    localguid=guid,
                    deletedfolder=self.params.deleted_folder,
                    scan=self.params.scan,
                    brandtemplate=self.params.brand_template,
                    securitypolicy=self.params.security_policy,
                )
                successful_records.append(record.to_json())
                successful_guids.append(guid)
            except ProofPointPSHTTPError as e:
                failed_entries.append({
                    "guid": guid,
                    "error": str(e)
                })
                if "folder" in str(e).lower():
                    folder_error = str(e)
                continue

        self.json_results = {
            "success": successful_records,
            "failed": failed_entries
        }

        if folder_error:
            self.result_value = False
            failed_details = [
                f"{entry.get('guid')} (Error: {entry.get('error')})"
                for entry in failed_entries
            ]
            self.output_message = (
                f"Failed to release quarantined email(s): {', '.join(failed_details)}"
            )
            return

        if not successful_guids:
            self.result_value = False
            failed_details = [
                f"{entry.get('guid')} (Error: {entry.get('error')})"
                for entry in failed_entries
            ]
            self.output_message = (
                f"Failed to release quarantined email(s): {', '.join(failed_details)}"
            )
            return

        if failed_entries:
            self.result_value = True
            failed_details = [
                f"{entry.get('guid')} (Error: {entry.get('error')})"
                for entry in failed_entries
            ]
            self.output_message = (
                f"Successfully released quarantined email(s): {', '.join(successful_guids)}. "
                f"Failed to release quarantined email(s): {', '.join(failed_details)}"
            )
            return

        self.result_value = True
        self.output_message = (
            f"Successfully released quarantined email(s): {', '.join(successful_guids)}"
        )


def main() -> None:
    ReleaseQuarantinedEmail().run()


if __name__ == "__main__":
    main()

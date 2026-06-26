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
from ..core.exceptions import ProofPointPSError, ProofPointPSHTTPError

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
        if not self.params.folder or self.params.folder == "None":
            self.params.folder = "Quarantine"
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
        folder_name = self.params.folder
        deleted_folder = self.params.deleted_folder

        if deleted_folder and folder_name.lower() == deleted_folder.lower():
            raise ProofPointPSError(
                "Failed to release quarantined email(s). Error: "
                "Folder and deleted folder cannot be the same."
            )

        try:
            self._validate_folder(folder_name, "Folder")
            records = self._pre_validate_guids(guids, folder_name)
            if deleted_folder:
                self._validate_folder(deleted_folder, "Deleted folder")
        except ProofPointPSError as e:
            raise ProofPointPSError(f"Failed to release quarantined email(s). Error: {e}")

        successful_records = []
        successful_guids = []

        records_map = {r.guid: r for r in records if r.guid}
        records_map.update({r.localguid: r for r in records if r.localguid})

        for guid in guids:
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
                record = records_map.get(guid)
                if record:
                    successful_records.append(record.to_json())
                successful_guids.append(guid)
            except ProofPointPSHTTPError as e:
                raise ProofPointPSError(
                    f"Failed to release quarantined email(s): GUID {guid} failed during execution. "
                    f"Error: {e}"
                )

        self.json_results = {
            "success": successful_records
        }
        self.result_value = True
        self.output_message = (
            f"Successfully released quarantined email(s): {', '.join(successful_guids)}"
        )



def main() -> None:
    ReleaseQuarantinedEmail().run()


if __name__ == "__main__":
    main()

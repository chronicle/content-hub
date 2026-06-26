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

import email
import pathlib
import re
import tempfile
from email.header import decode_header
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from ..core.base_action import BaseProofPointPSAction
from ..core.constants import DOWNLOAD_ACTION_NAME
from ..core.exceptions import ProofPointPSError, ProofPointPSHTTPError

if TYPE_CHECKING:
    from typing import Never


class DownloadQuarantinedEmail(BaseProofPointPSAction):
    """Download Quarantined Email action."""

    def __init__(self) -> None:
        super().__init__(DOWNLOAD_ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        """Extracts action-specific parameters."""
        self.params.guid_input = extract_action_param(
            self.soar_action,
            param_name="Message GUIDs",
            is_mandatory=True,
            print_value=True,
        )
        self.params.folder = extract_action_param(
            self.soar_action, param_name="Folder Name", print_value=True
        )
        if not self.params.folder or self.params.folder == "None":
            self.params.folder = "Quarantine"

    def _get_safe_subject(self, raw_content: bytes) -> str:
        """Extract and sanitize the Subject header from raw email bytes."""
        try:
            msg = email.message_from_bytes(raw_content)
            subject_header = msg.get("Subject", "")
            if not subject_header:
                return "NoSubject"

            decoded_parts = decode_header(subject_header)
            subject_parts = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    subject_parts.append(
                        part.decode(encoding or "utf-8", errors="replace")
                    )
                else:
                    subject_parts.append(str(part))

            subject = "".join(subject_parts)
            safe_subject = re.sub(r'[\\/*?:"<>|\s]+', "_", subject).strip("_")
            return safe_subject[:100] if safe_subject else "NoSubject"
        except Exception:
            return "Email"

    def _perform_action(self, _: Never) -> None:
        """Execute the download operation and attach raw email content to the case.

        Args:
            _: Never input.

        """
        guids = string_to_multi_value(self.params.guid_input)
        folder_name = self.params.folder

        try:
            self._validate_folder(folder_name, "Folder")
            self._pre_validate_guids(guids, folder_name)
        except ProofPointPSError as e:
            raise ProofPointPSError(f"Failed to download quarantined email(s). Error:\n{e}")

        successful_records = []
        successful_guids = []

        for guid in guids:
            try:
                raw_content = self.api_client.download_message(guid)
                record = self.api_client.get_record_by_guid(guid, folder=folder_name)
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    safe_subject = self._get_safe_subject(raw_content)
                    file_name = f"{guid}-{safe_subject}.eml"
                    temp_file_path = pathlib.Path(temp_dir) / file_name

                    temp_file_path.write_bytes(raw_content)

                    self.soar_action.add_attachment(
                        file_path=str(temp_file_path),
                        description=(
                            f"Quarantined email raw content for Message GUID {guid}."
                        ),
                    )
                if record:
                    successful_records.append(record.to_json())
                successful_guids.append(guid)
            except ProofPointPSHTTPError as e:
                raise ProofPointPSError(f"Failed to download quarantined email(s): GUID {guid} failed during execution. Error: {e}")

        self.json_results = {
            "success": successful_records
        }
        self.result_value = True
        self.output_message = (
            f"Successfully downloaded and attached quarantined email raw content "
            f"for Message GUID(s): {', '.join(successful_guids)}."
        )



def main() -> None:
    DownloadQuarantinedEmail().run()


if __name__ == "__main__":
    main()

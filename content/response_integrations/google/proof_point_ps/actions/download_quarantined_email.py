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
from email.header import decode_header
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from ..core.base_action import BaseProofPointPSAction
import datetime
from ..core.constants import DOWNLOAD_ACTION_NAME, TIME_FORMAT
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
        if not self.params.folder:
            self.params.folder = "Quarantine"
        self.params.download_folder_path = extract_action_param(
            self.soar_action,
            param_name="Download Folder Path",
            is_mandatory=True,
            print_value=True,
        )
        overwrite_raw = self.soar_action.parameters.get("Overwrite")
        if overwrite_raw is None:
            self.params.overwrite = True
        else:
            self.params.overwrite = str(overwrite_raw).lower() == "true"
        self.soar_action.LOGGER.info(f"Overwrite: {self.params.overwrite}")
        self.params.save_to_case_wall = extract_action_param(
            self.soar_action,
            param_name="Save To Case Wall",
            is_mandatory=False,
            print_value=True,
            input_type=bool,
        )

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


        dest_dir = pathlib.Path(self.params.download_folder_path)
        if not dest_dir.exists() or not dest_dir.is_dir():
            raise ProofPointPSError(
                "Failed to download quarantined email(s). Error: "
                f"Download folder path '{self.params.download_folder_path}' "
                "does not exist or is not a directory."
            )

        successful_records = []
        successful_guids = []
        failed_guids_errors = []
        existing_file_guids = []
        downloaded_files = []
        missing_guids = []

        start_date = (
            datetime.datetime.utcnow() - datetime.timedelta(days=30)
        ).strftime(TIME_FORMAT)
        end_date = datetime.datetime.utcnow().strftime(TIME_FORMAT)

        try:
            folder_records = self.api_client.search(
                sender="*",
                folder=folder_name,
                start_date=start_date,
                end_date=end_date,
            )
        except ProofPointPSError:
            raise ProofPointPSError(
                f"Folder '{folder_name}' does not exist."
            )

        folder_records_map = {r.guid: r for r in folder_records if r.guid}
        folder_records_map.update({r.localguid: r for r in folder_records if r.localguid})

        for guid in guids:
            try:
                record = folder_records_map.get(guid)
                if not record:
                    missing_guids.append(guid)
                    continue

                try:
                    raw_content = self.api_client.download_message(guid)
                except ProofPointPSError:
                    missing_guids.append(guid)
                    continue
                
                safe_subject = self._get_safe_subject(raw_content)
                file_name = f"{guid}-{safe_subject}.eml"
                target_file_path = dest_dir / file_name

                if not self.params.overwrite and target_file_path.exists():
                    existing_file_guids.append((guid, str(target_file_path)))
                    continue

                target_file_path.write_bytes(raw_content)
                downloaded_files.append((guid, target_file_path))

                if record:
                    record_json = record.to_json()
                    record_json["downloaded_file_path"] = str(target_file_path)
                    successful_records.append(record_json)
                successful_guids.append(guid)
            except (ProofPointPSHTTPError) as e:
                failed_guids_errors.append((guid, str(e)))
                
        if missing_guids:
            raise ProofPointPSError(
                "The following message guids were not found in Proofpoint: "
                f"{', '.join(list(set(missing_guids)))}."
            )
                

        if existing_file_guids or failed_guids_errors:
            error_messages = []
            if existing_file_guids:
                guids_str = ", ".join([g[0] for g in existing_file_guids])
                if len(existing_file_guids) == 1:
                    error_messages.append(
                        f"GUID {existing_file_guids[0][0]} failed during execution. "
                        f"Error: File '{existing_file_guids[0][1]}' already exists. "
                        "Please change the path or set parameter 'Overwrite' to True."
                    )
                else:
                    error_messages.append(
                        f"GUIDs {guids_str} failed during execution. "
                        "Error: File already exists. "
                        "Please change the path or set parameter 'Overwrite' to True."
                    )
            for guid, err in failed_guids_errors:
                error_messages.append(
                    f"GUID {guid} failed during execution. Error: {err}"
                )

            raise ProofPointPSError(
                f"Failed to download quarantined email(s): {' '.join(error_messages)}"
            )

        if self.params.save_to_case_wall:
            for guid, target_file_path in downloaded_files:
                self.soar_action.add_attachment(
                    file_path=str(target_file_path),
                    description=(
                        f"Quarantined email raw content for Message GUID {guid}."
                    ),
                )

        self.json_results = {
            "success": successful_records
        }
        self.result_value = True
        self.output_message = (
            "Successfully downloaded quarantined email raw content "
            f"for Message GUID(s): {', '.join(successful_guids)}."
        )



def main() -> None:
    DownloadQuarantinedEmail().run()


if __name__ == "__main__":
    main()

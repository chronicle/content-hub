from __future__ import annotations

import email
import os
import pathlib
import re
import shutil
import tempfile
from email.header import decode_header
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from ..core.base_action import BaseProofPointPSAction
from ..core.constants import DOWNLOAD_ACTION_NAME

if TYPE_CHECKING:
    from typing import Never, NoReturn


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
        successful_guids = []
        failed_guids = []

        for guid in guids:
            temp_dir = None
            try:
                raw_content = self.api_client.download_message(guid)

                temp_dir = tempfile.mkdtemp()
                safe_subject = self._get_safe_subject(raw_content)
                file_name = f"{guid}-{safe_subject}.eml"
                temp_file_path = os.path.join(temp_dir, file_name)

                pathlib.Path(temp_file_path).write_bytes(raw_content)

                try:
                    self.soar_action.add_attachment(
                        file_path=temp_file_path,
                        description=(
                            f"Quarantined email raw content for Message GUID {guid}."
                        ),
                    )
                    successful_guids.append(guid)
                finally:
                    if pathlib.Path(temp_dir).exists():
                        shutil.rmtree(temp_dir)
            except Exception as e:
                if temp_dir and pathlib.Path(temp_dir).exists():
                    shutil.rmtree(temp_dir)
                failed_guids.append((guid, str(e)))

        if not successful_guids:
            msg = (
                f"Failed to download any quarantined emails. Errors: "
                f"{'; '.join(f'{g}: {err}' for g, err in failed_guids)}"
            )
            raise Exception(
                msg
            )

        if failed_guids:
            self.result_value = False
            output_msg = "Failed to download some quarantined emails."
            if successful_guids:
                output_msg += f" Successfully downloaded and attached: {', '.join(successful_guids)}."
            output_msg += f" Failed for: {', '.join(f'{g} (Error: {err})' for g, err in failed_guids)}"
            self.output_message = output_msg
            return

        self.result_value = True
        self.output_message = f"Successfully downloaded and attached quarantined email raw content for Message GUID(s): {', '.join(successful_guids)}."


def main() -> NoReturn:
    DownloadQuarantinedEmail().run()


if __name__ == "__main__":
    main()

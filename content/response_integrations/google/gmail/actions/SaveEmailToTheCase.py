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

import requests

from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.exceptions import InternalJSONDecoderError
from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import save_attachment_to_case_wall
from TIPCommon.validation import ParameterValidator

from ..core.GoogleGmailApiManager import GoogleGmailApiManager
from ..core.GoogleGmailBaseAction import GoogleGmailBaseAction
from ..core.GoogleGmailConsts import (
    INTEGRATION_IDENTIFIER,
    SAVE_EMAIL_TO_THE_CASE,
    DEFAULT_MAILBOX,
)
from ..core.GoogleGmailDatamodel import GmailMessage
from ..core.GoogleGmailExceptions import GoogleGmailNotFoundError
from ..core.GoogleGmailServices import MessagesService


MESSAGE_NOT_FOUND = (
    "The message with the provided internet message ID {} was not found."
)
SUCCESS_MESSAGE = "Successfully saved the {} email."
SUCCESS_ATTACHMENTS = (
    "Successfully saved the following attachments from the {} email:\n{}.\n"
)
NOT_FOUND_ATTACHMENTS = (
    "The following attachments were not found in the {} email:\n{}.\n"
)
FAILED_ATTACHMENTS = (
    "The following attachments were not saved in the {} email due to an error:\n{}."
)
NO_ATTACHMENTS_SAVED = "No attachments were saved in the {} email."


class SaveEmailToTheCase(GoogleGmailBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.json_results = None
        self.result_value = False
        self.output_message = ""

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        super()._extract_action_parameters()

        self.params.mailbox = extract_action_param(
            self.soar_action,
            param_name="Mailbox",
            is_mandatory=True,
            print_value=True
        )
        self.params.message_id = extract_action_param(
            self.soar_action,
            param_name="Internet Message ID",
            is_mandatory=True,
            print_value=True
        )
        self.params.save_only_email_attachments = extract_action_param(
            self.soar_action,
            param_name="Save Only Email Attachments",
            input_type=bool,
            print_value=True
        )
        self.params.attachments_to_save = extract_action_param(
            self.soar_action,
            param_name="Attachment To Save",
            print_value=True
        )
        self.params.base64_encode = extract_action_param(
            self.soar_action,
            param_name="Base64 Encode",
            input_type=bool,
            print_value=True
        )

        if self.params.mailbox == DEFAULT_MAILBOX:
            self.params.mailbox = self.params.default_mailbox

    def _validate_params(self) -> None:
        super()._validate_params()
        validator = ParameterValidator(self.soar_action)
        validator.validate_email(
            "Mailbox",
            self.params.mailbox
        )

        self.params.attachments_list = validator.validate_csv(
            "Attachments Paths",
            self.params.attachments_to_save
        )

    def _init_api_clients(
            self,
            _: str | None = None
    ) -> GoogleGmailApiManager:
        """Initialize Api client."""
        return super()._init_api_clients(self.params.mailbox)

    def set_output_message_file_mode(
            self,
            saved_attachments: list[str],
            failed_attachments: list[str],
            not_found_attachments: set[str],
    ):
        """Set output messages when file mode is selected."""
        if not saved_attachments:
            self.output_message = NO_ATTACHMENTS_SAVED.format(self.params.message_id)
            return

        self.result_value = True
        self.output_message = SUCCESS_ATTACHMENTS.format(
            self.params.message_id,
            ",".join(saved_attachments)
        )

        if not_found_attachments:
            self.output_message += NOT_FOUND_ATTACHMENTS.format(
                self.params.message_id,
                ",".join(not_found_attachments)
            )

        if failed_attachments:
            self.output_message += FAILED_ATTACHMENTS.format(
                self.params.message_id,
                ",".join(failed_attachments)
            )

    def save_attachments_to_case_wall(self, message: GmailMessage) -> None:
        """Save message attachments to the case wall."""
        saved_attachments = []
        failed_attachments = []

        for attachment in message.payload.file_attachments:
            if (
                self.params.attachments_list
                and attachment.filename not in self.params.attachments_list
            ):
                continue

            attachment_ = attachment.create_case_wall_attachment_object()
            try:
                save_attachment_to_case_wall(
                    self.soar_action,
                    CaseWallAttachment(
                        name=attachment_.name,
                        base64_blob=attachment_.base64_blob,
                        file_type=attachment_.type,
                        is_important=False,
                    )
                )
                saved_attachments.append(attachment.filename)

            except (requests.HTTPError, InternalJSONDecoderError) as e:
                failed_attachments.append(attachment.filename)
                if not attachment_.type:
                    self.logger.error(
                        f"Attachment \"{attachment.filename}\" couldn't be proceed as "
                        "it's missing extension information. Skipping it"
                    )
                    continue

                self.logger.error(
                    f"Unable to save attachment \"{attachment.filename}\", "
                    f"the error is: {e}"
                )

        message_attachments = set(f.filename for f in message.payload.file_attachments)
        self.set_output_message_file_mode(
            saved_attachments,
            failed_attachments,
            set(self.params.attachments_list) - message_attachments
        )

    def save_message_to_case_wall(self, message: GmailMessage) -> None:
        """Save email message as a case-wall .eml attachment."""
        message_ = message.create_case_wall_attachment_object()
        save_attachment_to_case_wall(
            self.soar_action,
            CaseWallAttachment(
                name=message_.name,
                base64_blob=message_.base64_blob,
                file_type=message_.type,
                is_important=False,
            )
        )
        self.output_message = SUCCESS_MESSAGE.format(self.params.message_id)
        self.result_value = True

    async def _perform_action_async(self, _=None) -> None:
        async with self.api_client.session:
            gmail_service = MessagesService(
                api_manager=self.api_client,
                logger=self.logger,
                user_email=self.params.mailbox
            )

            message_ids = await gmail_service.search_by_message_id(
                self.params.message_id
            )
            if not message_ids:
                raise GoogleGmailNotFoundError(
                    MESSAGE_NOT_FOUND.format(self.params.message_id)
                )

            message = await gmail_service.get_message_by_id(message_ids[0])

            if (
                not self.params.save_only_email_attachments
                or self.params.base64_encode
            ):
                await gmail_service.set_message_mime_content(message)

            if self.params.save_only_email_attachments:
                await gmail_service.enrich_attachments(message.id, message.payload)

        if self.params.save_only_email_attachments:
            self.save_attachments_to_case_wall(message)
        else:
            self.save_message_to_case_wall(message)

        self.json_results = {
            **message.to_json(self.params.base64_encode),
            **message.payload.to_json()
        }

        await self.api_client.close()


def main() -> None:
    SaveEmailToTheCase(f"{INTEGRATION_IDENTIFIER} - {SAVE_EMAIL_TO_THE_CASE}").run()


if __name__ == "__main__":
    main()

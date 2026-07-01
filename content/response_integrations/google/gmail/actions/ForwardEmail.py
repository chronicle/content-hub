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

from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from ..core.GoogleGmailBaseAction import GoogleGmailBaseAction
from ..core.GoogleGmailConsts import (
    INTEGRATION_IDENTIFIER,
    FORWARD_EMAIL_SCRIPT_NAME,
    DEFAULT_MAILBOX,
)
from ..core.GoogleGmailExceptions import GoogleGmailNotFoundError
from ..core.GoogleGmailServices import MessagesService

MESSAGE_NOT_FOUND = (
    "The message with the provided internet message ID {} was not found. "
    "Check the spelling."
)
SUCCESS_MESSAGE = "Successfully forwarded the {} email"


class ForwardEmail(GoogleGmailBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.json_results = None
        self.output_message = ""

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        super()._extract_action_parameters()

        self.params.sender_from = extract_action_param(
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
        self.params.send_to = extract_action_param(
            self.soar_action,
            param_name="Send To",
            is_mandatory=True,
            print_value=True
        )
        self.params.subject = extract_action_param(
            self.soar_action,
            param_name="Subject",
            is_mandatory=True,
            print_value=True
        )
        self.params.cc = extract_action_param(
            self.soar_action,
            param_name="CC",
            print_value=True
        )
        self.params.bcc = extract_action_param(
            self.soar_action,
            param_name="BCC",
            print_value=True
        )
        self.params.attachments_paths = extract_action_param(
            self.soar_action,
            param_name="Attachments Paths",
            print_value=True
        )
        self.params.mail_content = extract_action_param(
            self.soar_action,
            param_name="Mail Content",
            is_mandatory=True,
            print_value=True
        )

        if self.params.sender_from == DEFAULT_MAILBOX:
            self.params.sender_from = self.params.default_mailbox

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        validator.validate_email(
            "Mailbox",
            self.params.sender_from
        )

        self.params.send_to_list = validator.validate_csv(
            "Send To",
            self.params.send_to
        )
        for item in self.params.send_to_list:
            validator.validate_email(
                "Send To",
                item
            )

        self.params.cc_list = validator.validate_csv(
            "CC",
            self.params.cc
        )
        for item in self.params.cc_list:
            validator.validate_email(
                "CC",
                item
            )

        self.params.bcc_list = validator.validate_csv(
            "BCC",
            self.params.bcc
        )
        for item in self.params.bcc_list:
            validator.validate_email(
                "BCC",
                item
            )

        self.params.attachments_list = validator.validate_csv(
            "Attachments Paths",
            self.params.attachments_paths
        )

    async def _perform_action_async(self, _=None) -> None:
        api_client = self._init_api_clients(self.params.sender_from)

        async with api_client.session:
            gmail_service = MessagesService(
                api_manager=api_client,
                logger=self.logger,
                user_email=self.params.sender_from
            )
            original_message_ids = await gmail_service.search_by_message_id(
                self.params.message_id
            )
            if not original_message_ids:
                raise GoogleGmailNotFoundError(
                    MESSAGE_NOT_FOUND.format(self.params.message_id)
                )

            original_message = await gmail_service.get_message_by_id(
                original_message_ids[0]
            )
            await gmail_service.set_message_mime_content(original_message)
            await gmail_service.enrich_attachments(
                original_message.id,
                original_message.payload,
            )

            message_meta = await gmail_service.forward_message(
                message=original_message,
                to=self.params.send_to_list,
                cc=self.params.cc_list,
                bcc=self.params.bcc_list,
                subject=self.params.subject,
                body=self.params.mail_content,
                attachments_paths=self.params.attachments_list,
            )
            message = await gmail_service.get_message_by_id(message_meta.id)

        self.output_message = SUCCESS_MESSAGE.format(self.params.message_id)
        self.json_results = {
            **message.to_json(),
            **message.payload.to_json()
        }

        await self.api_client.close()


def main() -> None:
    ForwardEmail(f"{INTEGRATION_IDENTIFIER} - {FORWARD_EMAIL_SCRIPT_NAME}").run()


if __name__ == "__main__":
    main()

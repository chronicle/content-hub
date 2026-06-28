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

from gmail.core.GoogleGmailBaseAction import GoogleGmailBaseAction
from gmail.core.GoogleGmailConsts import (
    INTEGRATION_IDENTIFIER,
    SEND_THREAD_REPLY_SCRIPT_NAME,
    DEFAULT_MAILBOX,
)
from gmail.core.GoogleGmailExceptions import GoogleGmailNotFoundError, GoogleGmailValidationError
from gmail.core.GoogleGmailServices import MessagesService

MESSAGE_NOT_FOUND = (
    "The message with the provided internet message ID {} was not found."
)
SUCCESS_MESSAGE = "Successfully sent a thread reply to the {} email."
ONLY_OWN_EMAIL_IN_RECIPIENTS = (
    "to send a reply to your email address, configure the “Reply To” parameter."
)


class SendThreadReply(GoogleGmailBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.json_results = None

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
        self.params.reply_to = extract_action_param(
            self.soar_action,
            param_name="Reply To",
            print_value=True
        )
        self.params.reply_all = extract_action_param(
            self.soar_action,
            param_name="Reply All",
            print_value=True,
            input_type=bool
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
        self.params.reply_to_list = validator.validate_csv(
            "Reply To",
            self.params.reply_to
        )
        for item in self.params.reply_to_list:
            validator.validate_email(
                "Reply To",
                item
            )

        if self.params.attachments_paths:
            self.params.attachments_paths = validator.validate_csv(
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
            await gmail_service.enrich_attachments(
                original_message.id,
                original_message.payload,
            )

            if self.params.reply_all:
                to = {
                    recipient for recipient in original_message.payload.all_recipients
                    + [original_message.payload.from_]
                    if recipient != gmail_service.user_email
                }
                if not to:
                    raise GoogleGmailValidationError(ONLY_OWN_EMAIL_IN_RECIPIENTS)
            else:
                to = self.params.reply_to_list or [original_message.payload.from_]

            message_meta = await gmail_service.reply_to_message(
                message=original_message,
                to=to,
                body=self.params.mail_content,
                attachments_paths=self.params.attachments_paths,
            )
            message = await gmail_service.get_message_by_id(message_meta.id)

        self.output_message = SUCCESS_MESSAGE.format(self.params.message_id)
        self.json_results = {
            **message.to_json(),
            **message.payload.to_json()
        }

        await self.api_client.close()


def main() -> None:
    SendThreadReply(f"{INTEGRATION_IDENTIFIER} - {SEND_THREAD_REPLY_SCRIPT_NAME}").run()


if __name__ == "__main__":
    main()

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

from TIPCommon.base.utils import validate_manager
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator

from ..core.GoogleGmailBaseAction import GoogleGmailBaseAction
from ..core.GoogleGmailConsts import (
    INTEGRATION_IDENTIFIER,
    SEND_EMAIL_SCRIPT_NAME,
    DEFAULT_MAILBOX,
)
from ..core.GoogleGmailServices import MessagesService


SUCCESS_MESSAGE = "Email was sent successfully."
ERROR_MESSAGE = "Failed to send email!"


class SendEmail(GoogleGmailBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
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
        self.params.reply_to_recipients = extract_action_param(
            self.soar_action,
            param_name="Reply-To Recipients",
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

        self.params.send_to = validator.validate_csv(
            "Send To",
            self.params.send_to
        )
        for item in self.params.send_to:
            validator.validate_email(
                "Send To",
                item
            )

        if self.params.cc:
            self.params.cc = validator.validate_csv(
                "CC",
                self.params.cc
            )
            for item in self.params.cc:
                validator.validate_email(
                    "CC",
                    item
                )

        if self.params.bcc:
            self.params.bcc = validator.validate_csv(
                "BCC",
                self.params.bcc
            )
            for item in self.params.bcc:
                validator.validate_email(
                    "BCC",
                    item
                )

        if self.params.attachments_paths:
            self.params.attachments_paths = validator.validate_csv(
                "Attachments Paths",
                self.params.attachments_paths
            )

        if self.params.reply_to_recipients:
            self.params.reply_to_recipients = validator.validate_csv(
                "Reply-To Recipients",
                self.params.reply_to_recipients
            )
            for item in self.params.reply_to_recipients:
                validator.validate_email(
                    "Reply-To Recipients",
                    item
                )

    async def _perform_action_async(self, _=None) -> None:
        api_client = self._init_api_clients(self.params.sender_from)

        async with api_client.session:
            self.logger.info("Validating manager is not None")
            validate_manager(api_client)
            self.logger.info("Testing connectivity")
            await api_client.test_connectivity()
            self.logger.info("Sending email")

            gmail_service = MessagesService(
                api_manager=api_client,
                logger=self.logger,
                user_email=self.params.sender_from
            )

            message_meta = await gmail_service.send_email(
                to=self.params.send_to,
                cc=self.params.cc,
                bcc=self.params.bcc,
                reply_to=self.params.reply_to_recipients,
                subject=self.params.subject,
                body=self.params.mail_content,
                attachments_paths=self.params.attachments_paths,
            )
            message = await gmail_service.get_message_by_id(message_meta.id)

            self.json_results = {
                **message.to_json(),
                **message.payload.to_json()
            }

        await self.api_client.close()


def main() -> None:
    SendEmail(f"{INTEGRATION_IDENTIFIER} - {SEND_EMAIL_SCRIPT_NAME}").run()


if __name__ == "__main__":
    main()

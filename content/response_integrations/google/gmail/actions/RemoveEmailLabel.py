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

import asyncio
import itertools

from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import unix_now
from TIPCommon.validation import ParameterValidator

from gmail.core.GoogleGmailApiManager import GoogleGmailApiManager
from gmail.core.GoogleGmailBaseAction import GoogleGmailBaseAction
from gmail.core.GoogleGmailConsts import (
    REMOVE_EMAIL_LABEL_SCRIPT_NAME,
    DEFAULT_MAILBOX,
)
from gmail.core.GoogleGmailDatamodel import MailboxReadEnum
from gmail.core.GoogleGmailExceptions import (
    GoogleGmailNotFoundError,
    GoogleGmailValidationError,
)
from gmail.core.GoogleGmailServices import MessagesService, LabelsService

SUCCESS_MESSAGE = (
    "Successfully updated labels for {} emails in the {} mailbox.\n"
)
LABELS_INVALID = (
    "The following labels don’t exist in the {} mailbox: {}"
)
ALL_LABELS_INVALID = (
    "None of the provided labels exists in the {} mailbox."
)
NO_MESSAGES_UPDATED_MESSAGE = (
    "The action did not find any emails based on the specified search criteria in "
    "the {}."
)
EMPTY_PARAMS_MESSAGE = (
    "configure the \"Internet Message ID\" parameter or one of the \"Subject Filter\", "
    "\"Labels Filter\", \"Sender Filter\", or \"Time Frame (minutes)\" parameters."
)


class RemoveEmailLabel(GoogleGmailBaseAction):
    __mailboxes_to_process_in_parallel = 10

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.result_value = True

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        super()._extract_action_parameters()
        self.params.mailbox = extract_action_param(
            self.soar_action,
            "Mailbox",
        )
        self.params.labels = extract_action_param(
            self.soar_action,
            "Labels Filter"
        )
        self.params.label = extract_action_param(
            self.soar_action,
            "Label"
        )
        self.params.message_id = extract_action_param(
            self.soar_action,
            "Internet Message ID"
        )
        self.params.subject_filter = extract_action_param(
            self.soar_action,
            "Subject Filter"
        )
        self.params.sender_filter = extract_action_param(
            self.soar_action,
            "Sender Filter",
            default_value=""
        )
        self.params.time_frame = extract_action_param(
            self.soar_action,
            "Time Frame (minutes)"
        )
        self.params.move_to_trash = extract_action_param(
            self.soar_action,
            "Move to Trash",
            input_type=bool
        )
        self.params.email_status = extract_action_param(
            self.soar_action,
            "Email Status"
        )
        if self.params.mailbox == DEFAULT_MAILBOX:
            self.params.mailbox = self.params.default_mailbox

    def _validate_params(self) -> None:
        """Validate action parameters."""
        super()._validate_params()
        validator = ParameterValidator(self.soar_action)
        self.params.mailbox = validator.validate_email(
            "Mailbox",
            self.params.mailbox
        )
        self.params.mailbox_read_status = MailboxReadEnum(
            validator.validate_ddl(
                "Email Status",
                self.params.email_status,
                ddl_values=[e.value for e in MailboxReadEnum]
            )
        )
        self.params.labels_list = set(
            label.lower() for label in
            validator.validate_csv(
                "Labels Filter",
                self.params.labels,
            )
        )
        self.params.labels_to_add = validator.validate_csv(
            "Label",
            self.params.label,
        )
        self.params.message_id_list = validator.validate_csv(
            "Internet Message ID",
            self.params.message_id
        )
        if self.params.sender_filter:
            self.params.sender_filter = validator.validate_email(
                "Sender Filter",
                self.params.sender_filter
            )
        if self.params.time_frame:
            self.params.time_frame = validator.validate_positive(
                "Time Frame (minutes)",
                self.params.time_frame
            )

        if not (
            self.params.message_id_list or
            any((
                self.params.subject_filter,
                self.params.sender_filter,
                self.params.time_frame,
                self.params.labels_list,
            ))
        ):
            raise GoogleGmailValidationError(EMPTY_PARAMS_MESSAGE)

    def _init_api_clients(
            self,
            _: str | None = None
    ) -> GoogleGmailApiManager:
        return super()._init_api_clients(self.params.mailbox)

    async def _get_message_ids(self, messages_service: MessagesService) -> list[str]:
        """Get message IDs to delete from initialized message service."""
        if self.params.message_id_list:
            return list(
                itertools.chain.from_iterable(
                    await asyncio.gather(
                        *(
                            messages_service.search_by_message_id(message_id)
                            for message_id in self.params.message_id_list
                        )
                    )
                )
            )

        return await messages_service.search_messages(
            after_ts=(
                unix_now() // NUM_OF_MILLI_IN_SEC -
                self.params.time_frame * 60
                if self.params.time_frame is not None
                else None
            ),
            subject_filter=self.params.subject_filter,
            sender_filter=self.params.sender_filter,
            labels=self.params.labels_list,
            mailbox_read_status=self.params.mailbox_read_status,
        )

    async def _perform_action_async(self, _=None) -> None:
        async with self.api_client.session:
            messages_service = MessagesService(
                api_manager=self.api_client,
                logger=self.logger,
                user_email=self.params.mailbox,
            )
            labels_service = LabelsService(
                api_manager=self.api_client,
                logger=self.logger,
                user_email=self.params.mailbox,
            )

            labels = await labels_service.list_labels()
            existing_labels = {label.name.casefold(): label for label in labels}
            labels_to_add = {}
            non_existing_labels = []
            for label_name in self.params.labels_to_add:
                if label_name.casefold() in labels_to_add:
                    continue

                label_ = existing_labels.get(label_name.casefold())
                if label_ is None:
                    non_existing_labels.append(label_name)
                    continue

                labels_to_add[label_name.casefold()] = label_

            if not labels_to_add:
                self.output_message = ALL_LABELS_INVALID.format(self.params.mailbox)
                self.result_value = False
                return

            message_ids = await self._get_message_ids(messages_service)
            if not message_ids:
                raise GoogleGmailNotFoundError(
                    NO_MESSAGES_UPDATED_MESSAGE.format(self.params.mailbox)
                )

            await messages_service.remove_labels(
                message_ids,
                [label_.id for label_ in labels_to_add.values()]
            )

        self.output_message = SUCCESS_MESSAGE.format(
            len(message_ids),
            self.params.mailbox
        )
        if non_existing_labels:
            self.output_message += LABELS_INVALID.format(
                self.params.mailbox,
                ",".join(non_existing_labels)
            )


def main() -> None:
    RemoveEmailLabel(REMOVE_EMAIL_LABEL_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

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
import json
import requests

from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.consts import TIMEOUT_THRESHOLD
from TIPCommon.base.data_models import ExecutionState
from TIPCommon.base.utils import coros_to_tasks_with_limit
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.exceptions import InternalJSONDecoderError
from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import save_attachment_to_case_wall
from TIPCommon.smp_time import unix_now
from TIPCommon.transformation import convert_dict_to_json_result_dict
from TIPCommon.validation import ParameterValidator

from ..core.GoogleGmailApiManager import GoogleGmailApiManager
from ..core.GoogleGmailBaseAction import GoogleGmailBaseAction
from ..core.GoogleGmailConsts import (
    DEFAULT_MAILBOX,
    WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
)
from ..core.GoogleGmailDatamodel import (
    MailboxProcessingInfo,
    MailboxProcessingStatus,
    GmailMessage,
)

from ..core.GoogleGmailExceptions import (
    GoogleGmailNotFoundError,
)
from ..core.GoogleGmailServices import MessagesService
from ..core.GoogleGmailUtils import TaskTimeoutGuard


MESSAGE_NOT_FOUND = (
    "The message with the provided internet message ID {} was not found."
)
SUCCESS_MESSAGE = (
    "Found replies from the following users: \n{}.\n"
)
PENDING_MESSAGE = (
    "Waiting for replies from the following users: \n{}."
)
FAILED_ATTACHMENTS = (
    "The following attachments were not returned in the {} email due to an error:"
    "\n{}.\n"
)
ASYNC_TIMOUT_WITH_SOME_FETCHED = (
    "Timeout reached when getting replies from the following users: \n{}\n"
    "Re-run the action to continue waiting for additional replies. Consider "
    "increasing the timeout in IDE."
)
ASYNC_TIMEOUT_MESSAGE = (
    "The action failed to receive any replies until reaching timeout. Re-run the "
    "action to continue waiting for replies. Consider increasing the timeout in IDE."
)


class WaitForThreadReply(GoogleGmailBaseAction):
    __messages_to_process_in_parallel = 15

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self._result_value = self.result_value = False
        self.action_context: MailboxProcessingInfo | None = None
        self.execution_state = ExecutionState.COMPLETED
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        super()._extract_action_parameters()
        self.params.mailbox = extract_action_param(
            self.soar_action,
            "Mailbox",
        )
        self.params.message_id = extract_action_param(
            self.soar_action,
            "Internet Message ID"
        )
        self.params.wait_for_all_replies = extract_action_param(
            self.soar_action,
            "Wait for All Recipients to Reply",
            input_type=bool
        )
        self.params.fetch_attachments = extract_action_param(
            self.soar_action,
            "Fetch Response Attachments",
            input_type=bool
        )

        self.params.additional_data = extract_action_param(
            self.soar_action,
            "additional_data",
            "{}"
        )

    def get_mailbox(self, validator: ParameterValidator) -> str:
        """Resolve mailbox parameter."""
        if self.params.mailbox == DEFAULT_MAILBOX:
            return self.params.default_mailbox

        return validator.validate_email(
            "Mailbox",
            self.params.mailbox,
        )

    def _validate_params(self) -> None:
        """Validate action parameters."""
        super()._validate_params()
        validator = ParameterValidator(self.soar_action)
        self.params.target_mailbox = self.get_mailbox(validator)

    def _init_api_clients(
            self,
            _: str | None = None
    ) -> GoogleGmailApiManager:
        return super()._init_api_clients(self.params.mailbox)

    def _get_actions_context(self) -> MailboxProcessingInfo:
        """Build action's context based on action parameters."""
        if self.is_first_run:
            return MailboxProcessingInfo(
                mailbox_name=self.params.mailbox
            )

        return MailboxProcessingInfo.from_dict(
            json.loads(self.params.additional_data)
        )

    def _set_action_result(self) -> None:
        """Set action result based on current action context."""
        replies_to_sender_map = {
            message["from"]: message
            for message in self.action_context.finished_operations_data
        }
        not_processed_replies = (
            set(self.action_context.extra_context["all_recipients"])
            .difference(replies_to_sender_map)
        )

        is_not_completed = (
            (not self.params.wait_for_all_replies and not replies_to_sender_map) or
            (self.params.wait_for_all_replies and not_processed_replies)
        )
        if is_not_completed and not self.is_approaching_async_timeout():
            self.output_message = PENDING_MESSAGE.format(
                ", ".join(not_processed_replies)
            )
            self.execution_state = ExecutionState.IN_PROGRESS
            self._result_value = json.dumps(self.action_context.as_dict())
            return

        if replies_to_sender_map:
            self.output_message = SUCCESS_MESSAGE.format(
                ", ".join(replies_to_sender_map)
            )
            self.result_value = True
            self.json_results = convert_dict_to_json_result_dict(replies_to_sender_map)

            failed_attachments_map = (
                self.action_context.extra_context.get("failed_attachments", {})
            )
            for message_id, attachment_names in failed_attachments_map.items():
                self.output_message += FAILED_ATTACHMENTS.format(
                    message_id, ",".join(attachment_names)
                )

            if self.params.wait_for_all_replies and not_processed_replies:
                self.output_message += ASYNC_TIMOUT_WITH_SOME_FETCHED.format(
                     ", ".join(not_processed_replies)
                )
                raise TimeoutError(self.output_message)

            return

        raise TimeoutError(ASYNC_TIMEOUT_MESSAGE)

    async def _filter_email(
            self,
            message_service: MessagesService,
            potential_reply_meta: GmailMessage,
    ) -> tuple[GmailMessage, bool]:
        if self.action_context.result_is_already_processed(
            potential_reply_meta.to_json(),
            extraction_func=lambda msg: msg["id"],
        ):
            self.logger.info(
                f"Message {potential_reply_meta.id} was already processed, skipping ..."
            )
            return potential_reply_meta, False

        if (
            potential_reply_meta.payload.from_
            in self.action_context.extra_context["all_recipients"]
            and potential_reply_meta.internal_date >=
            self.action_context.extra_context["internal_date"]
        ):
            self.logger.info(
                f"Message {potential_reply_meta.id} is a reply to original message,"
                f"fetching additional data."
            )
            message = await message_service.get_message_by_id(potential_reply_meta.id)
            if self.params.fetch_attachments:
                await message_service.enrich_attachments(message.id, message.payload)
            return message, True

        return potential_reply_meta, False

    async def _perform_action_async(self, _=None) -> None:
        self.action_context = self._get_actions_context()
        messages_service = MessagesService(
            api_manager=self.api_client,
            logger=self.logger,
            user_email=self.params.target_mailbox
        )
        source_message_id = await messages_service.search_by_message_id(
            self.params.message_id
        )
        if not source_message_id:
            raise GoogleGmailNotFoundError(
                MESSAGE_NOT_FOUND.format(self.params.message_id)
            )

        if self.is_first_run:
            source_message = await messages_service.get_message_by_id(
                source_message_id[-1],
                format_="metadata",
                metadata_headers=["to", "cc", "bcc", "message-id"]
            )
            self.action_context.status = MailboxProcessingStatus.STARTED
            self.action_context.extra_context = {
                "internal_date": source_message.internal_date,
                "all_recipients": source_message.payload.all_recipients,
                "thread_id": source_message.thread_id,
                "failed_attachments": {}
            }

        email_thread = await messages_service.get_thread_by_id(
            self.action_context.extra_context["thread_id"],
            format_="metadata",
            metadata_headers=["from"]
        )
        self.logger.info(
            f"Found {len(email_thread.messages)} potential replies, starting filtering."
        )
        filter_email_tasks = coros_to_tasks_with_limit(
            (
                self._filter_email(messages_service, message_meta)
                for message_meta in email_thread.messages
            ),
            self.__messages_to_process_in_parallel
        )

        concurrent_timeout = (
            (self.soar_action.script_timeout_deadline - unix_now())
            * TIMEOUT_THRESHOLD
            / NUM_OF_MILLI_IN_SEC
        )

        async with TaskTimeoutGuard(filter_email_tasks, self.logger):
            for filter_email_task in asyncio.as_completed(
                filter_email_tasks,
                timeout=min(concurrent_timeout, self.async_action_timeout)
            ):
                filtered_email, is_a_reply = await filter_email_task
                if is_a_reply is False:
                    continue

                self.action_context.extend_finished_operations(
                    (
                        {
                            **filtered_email.to_json(),
                            **filtered_email.payload.to_json()
                        },
                    )
                )
                if not self.params.fetch_attachments:
                    continue

                failed_attachments = (
                    self.action_context.extra_context["failed_attachments"]
                    .get(filtered_email.payload.message_id, [])
                )
                for attachment in filtered_email.payload.file_attachments:
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

                    except (requests.HTTPError, InternalJSONDecoderError) as e:
                        failed_attachments.append(attachment.filename)
                        if not attachment_.type:
                            self.logger.error(
                                f"Attachment \"{attachment.filename}\" couldn't be "
                                "proceed as it's missing extension information. "
                                "Skipping it"
                            )
                            continue

                        self.logger.error(
                            f"Unable to save attachment - {attachment.filename}, "
                            f"the error is: {e}"
                        )

                if failed_attachments:
                    attachments_map = (
                        self.action_context.extra_context["failed_attachments"]
                    )
                    attachments_map[filtered_email.payload.message_id] = (
                        failed_attachments
                    )

        self._set_action_result()
        await self.api_client.close()


def main() -> None:
    WaitForThreadReply(WAIT_FOR_THREAD_REPLY_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

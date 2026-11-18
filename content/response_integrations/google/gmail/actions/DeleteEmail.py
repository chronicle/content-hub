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
from TIPCommon.consts import TIMEOUT_THRESHOLD
from TIPCommon.base.data_models import ExecutionState
from TIPCommon.base.utils import coros_to_tasks_with_limit
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import unix_now
from TIPCommon.transformation import convert_dict_to_json_result_dict
from TIPCommon.validation import ParameterValidator

from ..core.GoogleGmailBaseAction import GoogleGmailBaseAction
from ..core.GoogleGmailConsts import (
    DELETE_EMAIL_SCRIPT_NAME,
)
from ..core.GoogleGmailDatamodel import AsyncMailboxesActionContext, MailboxReadEnum
from ..core.GoogleGmailExceptions import (
    GoogleCloudAuthenticationError,
    GoogleGmailNotFoundError,
    GoogleGmailPermissionDeniedError,
    GoogleGmailValidationError,
)
from ..core.GoogleGmailServices import MessagesService
from ..core.GoogleGmailUtils import TaskTimeoutGuard


SUCCESS_MESSAGE = (
    "Successfully deleted emails in the following mailboxes:\n{}\n\n"
)
NO_DELETED_MESSAGE = (
    "No deleted emails in the following mailboxes:\n{}\n\n"
)
PENDING_MESSAGE = (
    "Pending deletion of emails in the following mailboxes:\n{}\n"
)
UNFINISHED_MAILBOX_MESSAGE = (
    "The action wasn't able to complete deleting emails in the following mailboxes:"
    "\n{}\n. Please increase the timeout in the Google SecOps IDE and try again.\n\n"
)
NOT_FOUND_MAILBOX_MESSAGE = (
    "The following mailboxes were not found:\n{}\nCheck the spelling.\n\n"
)
NO_MAILBOXES_FOUND_MESSAGE = (
    "None of the provided mailboxes were found:\n{}\nCheck the spelling."
)
NO_MESSAGES_DELETED_MESSAGE = (
    "The action didn’t find any emails based on the specified search criteria."
)
EMPTY_PARAMS_MESSAGE = (
    "configure the \"Internet Message ID\" parameter or one of the \"Subject Filter\", "
    "\"Labels Filter\", \"Sender Filter\", or \"Time Frame (minutes)\" parameters."
)


class DeleteEmail(GoogleGmailBaseAction):
    __mailboxes_to_process_in_parallel = 10

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self._result_value = self.result_value = False
        self.action_context: AsyncMailboxesActionContext | None = None
        self.execution_state = ExecutionState.COMPLETED
        self.json_results = {}

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

        self.params.additional_data = extract_action_param(
            self.soar_action,
            "additional_data",
            "{}"
        )

    def _validate_params(self) -> None:
        """Validate action parameters."""
        super()._validate_params()
        validator = ParameterValidator(self.soar_action)
        self.params.mailboxes = validator.validate_csv(
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

        if self.params.move_to_trash and "trash" not in self.params.labels_list:
            self.params.labels_list.add("-trash")

    def _get_actions_context(self) -> AsyncMailboxesActionContext:
        """Build action's context based on action parameters."""
        if self.is_first_run:
            return AsyncMailboxesActionContext.from_mailboxes(
                self.params.mailboxes,
                self.params.default_mailbox,
            )

        return AsyncMailboxesActionContext.from_json(
            self.params.additional_data
        )

    def _prepare_statistics_message(self) -> str:
        """Prepare messages with statistics on finished mailboxes."""
        some_deleted = []
        no_deleted = []
        json_results = {}
        message = NO_MESSAGES_DELETED_MESSAGE

        for mailbox_info in self.action_context.processed_mailboxes:
            if not mailbox_info.found_emails:
                no_deleted.append(mailbox_info.mailbox_name)
                continue

            some_deleted.append(
                f"Deleted {mailbox_info.finished_emails} out of "
                f"{mailbox_info.found_emails} in {mailbox_info.mailbox_name}."
            )
            json_results[mailbox_info.mailbox_name] = (
                mailbox_info.finished_operations_data
            )

        self.json_results = convert_dict_to_json_result_dict(json_results)
        if some_deleted:
            message = SUCCESS_MESSAGE.format("\n".join(some_deleted))
            self.result_value = True

            if no_deleted:
                message += NO_DELETED_MESSAGE.format(", ".join(no_deleted))

        return message

    def _set_action_result(self) -> None:
        """Set action result based on current action context."""
        if (
            self.action_context.unfinished_mailboxes
            and not self.is_approaching_async_timeout()
        ):
            self.output_message = PENDING_MESSAGE.format(
                ", ".join(self.action_context.unfinished_mailboxes)
            )
            self.execution_state = ExecutionState.IN_PROGRESS
            self._result_value = self.action_context.as_json()
            return

        if self.action_context.processed_mailboxes:
            self.output_message = self._prepare_statistics_message()

            if self.action_context.failed_mailboxes:
                self.output_message += NOT_FOUND_MAILBOX_MESSAGE.format(
                    ", ".join(self.action_context.failed_mailboxes)
                )

            if not self.action_context.unfinished_mailboxes:
                return

        if self.action_context.unfinished_mailboxes:
            self.output_message += UNFINISHED_MAILBOX_MESSAGE.format(
                ", ".join(self.action_context.unfinished_mailboxes)
            )
            raise TimeoutError(self.output_message)

        raise GoogleGmailNotFoundError(
            NO_MAILBOXES_FOUND_MESSAGE.format(
                ", ".join(self.action_context.failed_mailboxes)
            )
        )

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

    async def _process_mailbox(self, mailbox_name: str) -> None:
        try:
            api_client = self._init_api_clients(mailbox_name)
            async with api_client.session:
                messages_service = MessagesService(
                    api_manager=api_client,
                    logger=self.logger,
                    user_email=mailbox_name
                )
                message_ids = await self._get_message_ids(messages_service)
                self.action_context.mark_mailbox_as_started(
                    mailbox_name,
                    len(message_ids)
                )
                self.logger.info(
                    f"Found {len(message_ids)} in mailbox {mailbox_name}"
                )

                delete_message_fn = (
                    messages_service.trash_message if self.params.move_to_trash is True
                    else messages_service.delete_message
                )
                delete_mail_tasks = coros_to_tasks_with_limit(
                    (delete_message_fn(message_id) for message_id in message_ids),
                    limit=10
                )

                try:
                    results = await asyncio.gather(
                        *delete_mail_tasks,
                        return_exceptions=True,
                    )
                    self.logger.info(
                        f"Finished {len(results)} delete operations for mailbox "
                        f"{mailbox_name}"
                    )
                    self.action_context.mark_mailbox_as_finished(mailbox_name, results)

                except asyncio.CancelledError:
                    self.action_context.mark_mailbox_as_partially_finished(
                        mailbox_name,
                        tuple(
                            task.result() for task in delete_mail_tasks
                            if task.done() and not task.cancelled()
                        )
                    )
                    raise

        except (
                GoogleCloudAuthenticationError,
                GoogleGmailNotFoundError,
                GoogleGmailPermissionDeniedError
        ):
            self.logger.info(f"Provided mailbox is not found: {mailbox_name}")
            self.action_context.mark_mailbox_as_failed(mailbox_name)
            return

    async def _perform_action_async(self, _=None) -> None:
        self.action_context = self._get_actions_context()
        process_tasks = coros_to_tasks_with_limit(
            (
                self._process_mailbox(mailbox_name)
                for mailbox_name in self.action_context.unfinished_mailboxes
            ),
            self.__mailboxes_to_process_in_parallel
        )
        concurrent_timeout = (
            (self.soar_action.script_timeout_deadline - unix_now())
            * TIMEOUT_THRESHOLD
            / NUM_OF_MILLI_IN_SEC
        )

        async with TaskTimeoutGuard(process_tasks, self.logger):
            for process_mailbox_coro in asyncio.as_completed(
                process_tasks,
                timeout=min(concurrent_timeout, self.async_action_timeout)
            ):
                await process_mailbox_coro

        self._set_action_result()
        await self.api_client.close()


def main() -> None:
    DeleteEmail(DELETE_EMAIL_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, MutableMapping, MutableSequence
import dataclasses
import json
from typing import NoReturn

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from TIPCommon.types import SingleJson
from TIPCommon.validation import ParameterValidator

from ..core.AsyncActionBaseClass import ActionResult, AsyncActionBaseClass
from ..core.MicrosoftGraphMailDelegatedManager import ApiManager
from ..core import constants
from ..core.datamodels import MicrosoftGraphEmail, MicrosoftGraphFolder
from ..core import utils


@dataclasses.dataclass(slots=True)
class ActionData:
    processed_mailboxes: MutableMapping[str, str]
    pending_mailboxes: MutableSequence[str]
    failed_mailboxes: MutableSequence[str]
    failed_folder_mailboxes: MutableSequence[str]
    all_deleted_emails: MutableSequence[MicrosoftGraphEmail]

    @classmethod
    def from_json(cls, json_data: MutableMapping[str, str]) -> ActionData:
        return cls(
            processed_mailboxes=json_data["processed_mailboxes"],
            pending_mailboxes=json_data["pending_mailboxes"],
            failed_mailboxes=json_data["failed_mailboxes"],
            failed_folder_mailboxes=json_data["failed_folder_mailboxes"],
            all_deleted_emails=json_data["all_deleted_emails"],
        )


def _delete_emails(
    manager: ApiManager,
    emails_to_delete: Iterable[MicrosoftGraphEmail],
) -> None:
    for email in emails_to_delete:
        manager.delete_email(email)


class DeleteEmailAction(AsyncActionBaseClass):

    def __init__(self, siemplify) -> None:
        super().__init__(siemplify)
        self.results = ActionData(
            processed_mailboxes={},
            pending_mailboxes=[],
            failed_mailboxes=[],
            failed_folder_mailboxes=[],
            all_deleted_emails=[],
        )

    def _extract_action_configuration(self) -> None:
        self.params.mailbox = extract_action_param(
            siemplify=self.siemplify,
            param_name="Delete In Mailbox",
            is_mandatory=True,
            default_value=self.params.api_params.mail_address,
            print_value=True,
        )
        self.params.mailbox = string_to_multi_value(
            self.params.mailbox, only_unique=True
        )
        self.params.folder_name = extract_action_param(
            siemplify=self.siemplify,
            param_name="Folder Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.email_ids = extract_action_param(
            siemplify=self.siemplify,
            param_name="Mail IDs",
            print_value=True,
        )
        self.params.email_ids = string_to_multi_value(
            self.params.email_ids,
            only_unique=True,
        )
        self.params.subject_filter = extract_action_param(
            siemplify=self.siemplify,
            param_name="Subject Filter",
            print_value=True,
        )
        self.params.sender_filter = extract_action_param(
            siemplify=self.siemplify,
            param_name="Sender Filter",
            print_value=True,
        )
        self.params.time_frame = extract_action_param(
            siemplify=self.siemplify,
            param_name="Time Frame (minutes)",
            print_value=True,
            input_type=int,
        )
        self.params.only_unread = extract_action_param(
            siemplify=self.siemplify,
            param_name="Only Unread",
            print_value=True,
            input_type=bool,
        )
        self.params.batch = extract_action_param(
            siemplify=self.siemplify,
            param_name="How many mailboxes to process in a single batch",
            default_value=constants.DEFAULT_BATCH_SIZE,
            input_type=int,
        )
        self.params.additional_data = extract_action_param(
            siemplify=self.siemplify,
            param_name="additional_data",
            default_value="{}",
        )
        self.params.limit_json_result = extract_action_param(
            siemplify=self.siemplify,
            param_name="Limit the Amount of Information Returned in the JSON Result",
            input_type=bool,
            default_value=False,
            print_value=True,
        )

        self.params.disable_json_result = extract_action_param(
            siemplify=self.siemplify,
            param_name="Disable the Action JSON Result",
            input_type=bool,
            default_value=True,
            print_value=True,
        )

    def _validate_params(self, validator: ParameterValidator) -> None:
        validator.validate_lower_limit(
            param_name="How many mailboxes to process in a single batch",
            value=self.params.batch,
            limit=1,
        )
        for email in self.params.mailbox:
            email: str = (
                self.params.api_params.mail_address
                if email == constants.DEFAULT_MAILBOX
                else email
            )
            validator.validate_email(param_name="Delete In Mailbox", email=email)

        if (
            self.params.time_frame is not None
            and self.params.time_frame <= constants.TIME_FRAME_THRESHOLD
        ):
            raise ValueError(
                'Please provide positive number in parameter "Time Frame (minutes)".'
            )

        self.params.additional_data = validator.validate_json(
            param_name="additional_data",
            json_string=self.params.additional_data,
            default_value="{}",
            print_value=False,
        )
        self.params.results = (
            ActionData.from_json(self.params.additional_data)
            if self.params.additional_data
            else self.results
        )

    def _perform_action(self, manager: ApiManager) -> ActionResult:
        self._set_action_data(manager=manager)
        self.validate_mailbox()

        batch: list[str] = self._get_mailboxes_batch()
        self.logger.info(
            f"Processing {len(batch)} mailboxes out of "
            f"{len(self.results.pending_mailboxes)} pending mailboxes."
        )
        mailboxes: utils.MailboxResult = utils.get_mailboxes_result(
            manager=manager,
            mailboxes=batch,
            folder_name=self.params.folder_name,
        )
        emails_to_delete: list[MicrosoftGraphEmail] = self._get_emails_to_delete(
            manager=manager,
            mailboxes=mailboxes.valid_mailboxes,
        )
        emails_to_delete = utils.get_emails_with_updated_metadata(
            manager=manager,
            emails=emails_to_delete,
            smime_auth=self.params.smime_auth,
        )
        _delete_emails(manager=manager, emails_to_delete=emails_to_delete)
        self._set_action_result(mailboxes=mailboxes, emails=emails_to_delete)
        self._log_messages()

        return self._finalize_action()

    def _set_action_data(self, manager: ApiManager) -> None:
        """Set mailbox data into the results attribute. if it's first run set all
            mailboxes to pending_mailboxes in result attribute otherwise
            additional data from async run.

        Args:
            valid_mailboxes (list[str]): A list of mailboxes that are searchable.
            invalid_mailboxes (list[str]): A list of mailboxes that are
                unsearchable.
        """
        additional_data: SingleJson = self.params.additional_data
        if not additional_data:
            valid_mailboxes, invalid_mailboxes = utils.filter_valid_invalid_mailboxes(
                manager=manager,
                mailboxes=self.params.mailbox,
                default_mailbox=self.params.api_params.mail_address,
            )
            self.results.failed_mailboxes.extend(invalid_mailboxes)
            self.results.pending_mailboxes = valid_mailboxes

        else:
            self.results = ActionData.from_json(additional_data)

    def _get_mailboxes_batch(self) -> MutableSequence[str]:
        pending_mailboxes: MutableSequence[str] = self.results.pending_mailboxes

        return pending_mailboxes[: self.params.batch]

    def _get_emails_to_delete(
        self,
        manager: ApiManager,
        mailboxes: Iterable[MicrosoftGraphFolder],
    ) -> Iterable[MicrosoftGraphEmail] | SingleJson:
        """Get emails to delete based on specified criteria.

        Args:
            manager (ApiManager): ApiManager instance.
            mailboxes (Iterable[MicrosoftGraphFolder]): List of MicrosoftGraphFolder
            object to search.

        Returns:
            Iterable[MicrosoftGraphEmail]: List of emails to be deleted.

        Note:
            If `email_ids` are provided, emails with matching IDs will be retrieved.
            Otherwise, a search is performed based on specified filters.
        """

        if not self.params.email_ids:
            mailboxes: MutableSequence[MicrosoftGraphFolder] = (
                utils.update_search_filters(
                    folders=mailboxes,
                    subject_filter=self.params.subject_filter,
                    sender_filter=self.params.sender_filter,
                    time_filter=self.params.time_frame,
                    only_unread=self.params.only_unread,
                )
            )

            return manager.search_emails(mailboxes)

        return utils.get_emails_with_email_ids(
            manager=manager,
            mailboxes=mailboxes,
            email_ids=self.params.email_ids,
        )

    def _set_action_result(
        self,
        mailboxes: utils.MailboxResult,
        emails: Iterable[MicrosoftGraphEmail],
    ) -> None:
        """Set the result of pending, processed and failed mailboxes.

        Args:
            mailboxes (MailboxResult): The result of processing mailboxes.
            emails (Iterable[MicrosoftGraphEmail]): List of deleted emails.
        """
        _update_emails_to_mailboxes(
            emails=emails,
            mailbox_data=self.results.processed_mailboxes,
        )
        self.results.failed_mailboxes.extend(mailboxes.invalid_mailboxes)
        self.results.failed_folder_mailboxes.extend(mailboxes.invalid_folder_mailboxes)
        self.results.pending_mailboxes = self.results.pending_mailboxes[
            self.params.batch :
        ]
        self.results.all_deleted_emails.extend([email.to_json() for email in emails])

    def _set_json_result(self) -> None:
        """Add json result to the case."""
        if self.params.disable_json_result or not self.results.all_deleted_emails:
            return

        json_result: MutableSequence[SingleJson] = [
            (
                self._create_compact_json_from_mail_json(email)
                if self.params.limit_json_result
                else email
            )
            for email in self.results.all_deleted_emails
        ]
        self.siemplify.result.add_result_json(json_result)

    def _create_compact_json_from_mail_json(
        self,
        email: MutableMapping[str, str],
    ) -> MutableMapping[str, str]:
        return MicrosoftGraphEmail(
            raw_data=email,
            folder_name=self.params.folder_name,
            mailbox_name=None,
            mail_id=email["id"],
            **email,
        ).to_compact_json()

    def _log_messages(self) -> None:
        self.logger.info(self._all_deleted_emails_msg)

        if self.results.failed_mailboxes:
            self.logger.error(self._mailbox_err_msg)

        if self.results.failed_folder_mailboxes:
            self.logger.error(self._folder_err_msg)

    def _finalize_action(self) -> ActionResult:
        if self._is_timeout():
            return self._finalize_action_on_timeout()

        if self.results.pending_mailboxes:
            return self._finalize_action_on_inprogress()

        if not self.results.processed_mailboxes:
            return self._finalize_action_on_failure()

        return self._finalize_action_on_success()

    def _finalize_action_on_timeout(self) -> ActionResult:
        has_processed_emails: bool = utils.has_processed_emails(
            self.results.processed_mailboxes
        )
        if self.results.processed_mailboxes and has_processed_emails:
            self.output_messages.append(self._timeout_with_success_msg)
            self.output_messages.append(self._mailbox_err_msg)
            self.output_messages.append(self._folder_err_msg)

            return ActionResult(ExecutionState.TIMED_OUT, True)

        message: str = "Action failed to delete any mails until timeout."
        self.output_messages.append(message)

        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_inprogress(self) -> ActionResult:
        message: str = (
            f"Successfully processed mailboxes: {len(self.results.processed_mailboxes)}"
            f", Pending mailboxes: {len(self.results.pending_mailboxes)}. Continuing..."
        )
        self.output_messages.append(message)

        return ActionResult(
            ExecutionState.IN_PROGRESS, json.dumps(dataclasses.asdict(self.results))
        )

    def _finalize_action_on_failure(self) -> ActionResult:
        all_failed_mailboxes: bool = set(self.results.failed_mailboxes) == set(
            self.params.mailbox
        )
        if all_failed_mailboxes:
            self.output_messages.append(self._no_mailbox_err_msg)
        else:
            self.output_messages.append(self._success_without_emails_msg)
            self.output_messages.append(self._mailbox_err_msg)
            self.output_messages.append(self._folder_err_msg)

        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_success(self) -> ActionResult:
        self._set_json_result()
        self.output_messages.append(self._success_with_emails_msg)
        self.output_messages.append(self._mailbox_err_msg)
        self.output_messages.append(self._folder_err_msg)

        return ActionResult(ExecutionState.COMPLETED, True)

    @property
    def _all_deleted_emails_msg(self) -> str:
        message: str = "Deleted mails with provided search criteria:"
        for mailbox, emails in self.results.processed_mailboxes.items():
            message += f"\n{mailbox}: {len(emails)}"

        return message

    @property
    def _success_with_emails_msg(self) -> str:
        message: str = "Successfully deleted emails in the following mailboxes: "
        for mailbox, messages in self.results.processed_mailboxes.items():
            message += f"\n{mailbox}: {len(messages)}"

        return message

    @property
    def _success_without_emails_msg(self) -> str:
        return (
            "The action didn't find any emails based on the specified search criteria"
        )

    @property
    def _timeout_with_success_msg(self) -> str:
        processed_mailboxes_str: str = convert_list_to_comma_string(
            list(self.results.processed_mailboxes), delimiter=", "
        )
        pending_mailboxes_str: str = convert_list_to_comma_string(
            self.results.pending_mailboxes, delimiter=", "
        )
        return (
            "Action ran into a timeout during execution.\n"
            f"Processed mailboxes: {processed_mailboxes_str}\n"
            f"Pending mailboxes: {pending_mailboxes_str}\n"
            "Please increase the timeout in IDE."
        )

    @property
    def _timeout_with_failure_msg(self) -> str:
        return "Action failed to delete any mails until timeout."

    @property
    def _mailbox_err_msg(self) -> str:
        if not self.results.failed_mailboxes:
            return ""

        failed_mailboxes: str = convert_list_to_comma_string(
            self.results.failed_mailboxes,
            delimiter=", ",
        )

        return f"The following mailboxes were not found: {failed_mailboxes}"

    @property
    def _folder_err_msg(self) -> str:
        if not self.results.failed_folder_mailboxes:
            return ""

        failed_folder_mailboxes: str = convert_list_to_comma_string(
            self.results.failed_folder_mailboxes, delimiter=", "
        )

        return (
            "The action failed to delete any emails because the provided mailbox "
            "folder name was not found in the following mailbox(es):\n"
            f"{failed_folder_mailboxes}: {self.params.folder_name}"
        )

    @property
    def _no_mailbox_err_msg(self) -> str:
        if not self.results.failed_mailboxes:
            return ""

        failed_mailboxes: str = convert_list_to_comma_string(
            self.results.failed_mailboxes,
            delimiter=", ",
        )

        return (
            "The action failed to find any of the provided mailboxes:\n "
            f"{failed_mailboxes}"
        )


def _update_emails_to_mailboxes(
    emails: Iterable[MicrosoftGraphEmail],
    mailbox_data: SingleJson,
) -> None:
    """Update a dictionary with email IDs grouped by mailbox.

    This function takes a list of MicrosoftGraphEmail objects and updates
    a dictionary (mailbox_data) with email IDs grouped by their associated
    mailbox names. Each mailbox in the dictionary will have a list of unique
    email IDs.

    Args:
        emails (Iterable[MicrosoftGraphEmail]): A list of MicrosoftGraphEmail
            objects containing mailbox information.
        mailbox_data (SingleJson): A dictionary to be updated with mailbox
            names as keys and lists of associated email IDs.
    """
    mailbox_to_email_ids: SingleJson = defaultdict(set)
    for email in emails:
        mailbox_to_email_ids[email.mailbox_name].add(email.id)

    for mailbox, email_ids in mailbox_to_email_ids.items():
        mailbox_data[mailbox] = list(email_ids)


@output_handler
def main() -> NoReturn:
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.script_name = constants.DELETE_EMAIL_SCRIPT_NAME
    action: DeleteEmailAction = DeleteEmailAction(siemplify)
    action.run()


if __name__ == "__main__":
    main()

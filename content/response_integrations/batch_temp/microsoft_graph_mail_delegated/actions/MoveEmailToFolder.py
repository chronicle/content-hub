from __future__ import annotations

from typing import NoReturn

from collections.abc import Iterable, MutableMapping, MutableSequence
from collections import defaultdict
import dataclasses
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from TIPCommon.types import SingleJson
from TIPCommon.validation import ParameterValidator

from ..core.AsyncActionBaseClass import ActionDataJson, ActionResult, AsyncActionBaseClass
from ..core.MicrosoftGraphMailDelegatedManager import ApiManager
from ..core import constants
from ..core import MicrosoftGraphMailDelegatedParser as parser

from ..core.datamodels import MicrosoftGraphEmail, MicrosoftGraphFolder
from ..core import utils


@dataclasses.dataclass(slots=True)
class ActionData:
    processed_mailboxes: MutableMapping[str, str]
    pending_mailboxes: MutableSequence[str]
    failed_mailboxes: MutableSequence[str]
    failed_folder_mailboxes: MutableSequence[str]
    failed_dst_folder_mailboxes: MutableSequence[str]

    @classmethod
    def from_json(cls, json_data: ActionDataJson) -> ActionData:
        return cls(
            processed_mailboxes=json_data["processed_mailboxes"],
            pending_mailboxes=json_data["pending_mailboxes"],
            failed_mailboxes=json_data["failed_mailboxes"],
            failed_folder_mailboxes=json_data["failed_folder_mailboxes"],
            failed_dst_folder_mailboxes=json_data["failed_dst_folder_mailboxes"],
        )


def _move_emails(
    manager: ApiManager,
    emails_to_move: Iterable[MicrosoftGraphEmail],
    folder_name_dst: str,
) -> MutableSequence[MicrosoftGraphEmail]:
    moved_mails: MutableSequence[MicrosoftGraphEmail] = []
    for email in emails_to_move:
        moved_email = manager.move_email_to_folder(
            email=email,
            destination_folder=folder_name_dst,
        )
        moved_mails.append(moved_email)

    return moved_mails


class MoveEmailAction(AsyncActionBaseClass):

    def __init__(self, siemplify) -> None:
        super().__init__(siemplify)
        self.results = ActionData(
            processed_mailboxes={},
            pending_mailboxes=[],
            failed_mailboxes=[],
            failed_folder_mailboxes=[],
            failed_dst_folder_mailboxes=[],
        )

    def _extract_action_configuration(self):
        self.params.mailbox = extract_action_param(
            siemplify=self.siemplify,
            param_name="Move In Mailbox",
            is_mandatory=True,
            default_value=self.params.api_params.mail_address,
            print_value=True,
        )
        self.params.mailbox = string_to_multi_value(
            self.params.mailbox,
            only_unique=True,
        )
        self.params.folder_name = extract_action_param(
            siemplify=self.siemplify,
            param_name="Source Folder Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.destination_folder = extract_action_param(
            siemplify=self.siemplify,
            param_name="Destination Folder Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.mail_ids = extract_action_param(
            siemplify=self.siemplify,
            param_name="Mail IDs",
            print_value=True,
        )
        self.params.mail_ids = string_to_multi_value(
            self.params.mail_ids,
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
            input_type=int,
            print_value=True,
        )
        self.params.only_unread = extract_action_param(
            siemplify=self.siemplify,
            param_name="Only Unread",
            print_value=True,
            default_value=False,
            input_type=bool,
        )
        self.params.batch = extract_action_param(
            siemplify=self.siemplify,
            param_name="How many mailboxes to process in a single batch",
            is_mandatory=False,
            default_value=constants.DEFAULT_BATCH_SIZE,
            input_type=int,
        )
        self.params.limit_json_result = extract_action_param(
            siemplify=self.siemplify,
            param_name="Limit the Amount of Information Returned in the JSON Result",
            input_type=bool,
            default_value=False,
            print_value=True
        )

        self.params.disable_json_result = extract_action_param(
            siemplify=self.siemplify,
            param_name="Disable the Action JSON Result",
            input_type=bool,
            default_value=False,
            print_value=True
        )
        self.params.additional_data = extract_action_param(
            siemplify=self.siemplify,
            param_name="additional_data",
            default_value="{}",
        )

    def _validate_params(self, validator: ParameterValidator) -> None:
        validator.validate_lower_limit(
            param_name="How many mailboxes to process in a single batch",
            value=self.params.batch,
            limit=1,
        )
        for email in self.params.mailbox:
            email = (
                self.params.api_params.mail_address
                if email == constants.DEFAULT_MAILBOX
                else email
            )
            validator.validate_email(param_name="Move In Mailbox", email=email)

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

    def _perform_action(self, manager: ApiManager) -> tuple[int, bool]:
        self._set_action_data(manager=manager)
        self.validate_mailbox()
        batch = self._get_mailboxes_batch()
        self.logger.info(
            f"Processing {len(batch)} mailboxes out of "
            f"{len(self.results.pending_mailboxes)} pending mailboxes."
        )
        mailbox_result_src = utils.get_mailboxes_result(
            manager=manager,
            mailboxes=batch,
            folder_name=self.params.folder_name,
        )
        mailbox_result_dst = utils.get_mailboxes_result(
            manager=manager,
            mailboxes=batch,
            folder_name=self.params.destination_folder,
        )
        valid_mailboxes = _get_common_valid_mailboxes(
            src_mailboxes=mailbox_result_src.valid_mailboxes,
            dst_mailboxes=mailbox_result_dst.valid_mailboxes,
        )
        emails_to_move = self._get_emails_to_move(
            manager=manager,
            mailboxes=valid_mailboxes,
        )
        moved_emails = _move_emails(
            manager=manager,
            emails_to_move=emails_to_move,
            folder_name_dst=self.params.destination_folder,
        )
        moved_emails = utils.get_emails_with_updated_metadata(
            manager=manager,
            emails=moved_emails,
            smime_auth=self.params.smime_auth,
        )
        self._set_action_result(
            src_mailboxes=mailbox_result_src,
            dst_mailboxes=mailbox_result_dst,
            emails=moved_emails,
        )
        self._set_json_result()
        self._log_messages()

        return self._finalize_action()

    def _set_action_data(self, manager: ApiManager) -> None:
        """Sets the action data.

        Args:
            manager (ApiManager): ApiManager instance.
        """
        additional_data = self.params.additional_data
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
        pending_mailboxes = self.results.pending_mailboxes

        return pending_mailboxes[: self.params.batch]

    def _get_emails_to_move(
        self,
        manager: ApiManager,
        mailboxes: Iterable[MicrosoftGraphFolder],
    ) -> Iterable[MicrosoftGraphEmail]:
        """Get emails to delete based on specified criteria.

        Args:
            manager (ApiManager): ApiManager instance.
            mailboxes (Iterable[MicrosoftGraphFolder]): List of MicrosoftGraphFolder
            object to search.

        Returns:
            Iterable[MicrosoftGraphEmail]: List of emails to be deleted.

        Note:
            If `mail_ids` are provided, emails with matching IDs will be retrieved.
            Otherwise, a search is performed based on specified filters.
        """

        if not self.params.mail_ids:
            mailboxes = utils.update_search_filters(
                folders=mailboxes,
                subject_filter=self.params.subject_filter,
                sender_filter=self.params.sender_filter,
                time_filter=self.params.time_frame,
                only_unread=self.params.only_unread,
            )

            return manager.search_emails(mailboxes)

        return utils.get_emails_with_email_ids(
            manager=manager,
            mailboxes=mailboxes,
            email_ids=self.params.mail_ids,
        )

    def _set_action_result(
        self,
        src_mailboxes: utils.MailboxResult,
        dst_mailboxes: utils.MailboxResult,
        emails: Iterable[MicrosoftGraphEmail],
    ) -> None:
        """Set the result of pending, processed and failed mailboxes.

        Args:
            src_mailboxes (utils.MailboxResult): The result of processing mailboxes with
                source folder.
            dst_mailboxes (utils.MailboxResult): The result of processing mailboxes with
                destination folder.
            emails (Iterable[MicrosoftGraphEmail]): List of moved emails.
        """
        _update_emails_to_mailboxes(
            emails=emails,
            mailbox_data=self.results.processed_mailboxes,
        )
        src_mailboxes.invalid_mailboxes.extend(dst_mailboxes.invalid_mailboxes)
        self.results.failed_mailboxes.extend(set(src_mailboxes.invalid_mailboxes))
        self.results.failed_folder_mailboxes.extend(
            src_mailboxes.invalid_folder_mailboxes
        )
        self.results.failed_dst_folder_mailboxes.extend(
            dst_mailboxes.invalid_folder_mailboxes
        )
        self.results.pending_mailboxes = self.results.pending_mailboxes[
            self.params.batch :
        ]

    def _set_json_result(self) -> None:
        """Add json result to the case."""
        if self.params.disable_json_result:
            return

        if not self.results.processed_mailboxes:
            self.siemplify.result.add_result_json([])
            return

        if self.params.limit_json_result:
            json_result_emails = [
                {
                    "Mailbox": mailbox,
                    "Emails": [
                        email.to_compact_json()
                        for email in parser.build_mg_emails(
                            alerts_data=emails,
                            folder_name=self.params.folder_name,
                            mailbox_name=mailbox,
                        )
                    ],
                }
                for mailbox, emails in self.results.processed_mailboxes.items()
            ]
        else:
            json_result_emails = [
                {"Mailbox": mailbox, "Emails": emails}
                for mailbox, emails in self.results.processed_mailboxes.items()
            ]

        self.siemplify.result.add_result_json(json_result_emails)

    def _log_messages(self) -> None:
        self.logger.info(self._all_moved_emails_msg)

        if self.results.failed_mailboxes:
            self.logger.error(self._mailbox_err_msg)

        if self.results.failed_folder_mailboxes:
            self.logger.error(self._src_folder_err_msg)

        if self.results.failed_dst_folder_mailboxes:
            self.logger.error(self._dst_folder_err_msg)

    def _finalize_action(self) -> ActionResult:
        if self._is_timeout():
            return self._finalize_action_on_timeout()

        if self.results.pending_mailboxes:
            return self._finalize_action_on_inprogress()

        if not self.results.processed_mailboxes:
            return self._finalize_action_on_failure()

        return self._finalize_action_on_success()

    def _finalize_action_on_timeout(self) -> ActionResult:
        has_processed_emails = utils.has_processed_emails(
            self.results.processed_mailboxes
        )
        if self.results.processed_mailboxes and has_processed_emails:
            self.output_messages.append(self._timeout_with_success_msg)
            self.output_messages.append(self._mailbox_err_msg)
            self.output_messages.append(self._src_folder_err_msg)
            self.output_messages.append(self._dst_folder_err_msg)

            return ActionResult(ExecutionState.TIMED_OUT, True)

        self.output_messages.append(self._timeout_with_failure_msg)

        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_inprogress(self) -> ActionResult:
        message: str = (
            f"Successfully processed mailboxes: {len(self.results.processed_mailboxes)}"
            f", Pending mailboxes: {len(self.results.pending_mailboxes)}. Continuing..."
        )
        self.output_messages.append(message)

        return ActionResult(
            ExecutionState.IN_PROGRESS,
            json.dumps(dataclasses.asdict(self.results)),
        )

    def _finalize_action_on_failure(self) -> ActionResult:
        all_failed_mailboxes = set(self.results.failed_mailboxes) == set(
            self.params.mailbox
        )
        if not all_failed_mailboxes:
            self.output_messages.append(self._success_without_emails_msg)
            self.output_messages.append(self._mailbox_err_msg)
            self.output_messages.append(self._src_folder_err_msg)
            self.output_messages.append(self._dst_folder_err_msg)

        else:
            self.output_messages.append(self._no_mailbox_err_msg)

        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_success(self) -> ActionResult:
        self.output_messages.append(self._success_with_emails_msg)
        self.output_messages.append(self._mailbox_err_msg)
        self.output_messages.append(self._src_folder_err_msg)
        self.output_messages.append(self._dst_folder_err_msg)

        return ActionResult(ExecutionState.COMPLETED, True)

    @property
    def _all_moved_emails_msg(self) -> str:
        message: str = "Moved mails with provided search criteria:"
        for mailbox, emails in self.results.processed_mailboxes.items():
            message += f"\n{mailbox}: {len(emails)}"

        return message

    @property
    def _success_with_emails_msg(self) -> str:
        message: str = "Successfully moved emails in the following mailboxes: "
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
            list(self.results.processed_mailboxes),
            delimiter=", ",
        )
        pending_mailboxes_str: str = convert_list_to_comma_string(
            self.results.pending_mailboxes,
            delimiter=", ",
        )
        return (
            "Action ran into a timeout during execution.\n"
            f"Processed mailboxes: {processed_mailboxes_str}\n"
            f"Pending mailboxes: {pending_mailboxes_str}\n"
            "Please increase the timeout in IDE."
        )

    @property
    def _timeout_with_failure_msg(self) -> str:
        return "Action failed to move any mails until timeout."

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
    def _src_folder_err_msg(self) -> str:
        if not self.results.failed_folder_mailboxes:
            return ""

        failed_folder_mailboxes = convert_list_to_comma_string(
            self.results.failed_folder_mailboxes, delimiter=", "
        )

        return (
            f"The action failed to move any emails because the provided source "
            "folder was not found in the following mailbox(es):\n"
            f"{failed_folder_mailboxes}: {self.params.folder_name}"
        )

    @property
    def _dst_folder_err_msg(self) -> str:
        if not self.results.failed_dst_folder_mailboxes:
            return ""

        failed_folder_mailboxes: str = convert_list_to_comma_string(
            self.results.failed_dst_folder_mailboxes,
            delimiter=", ",
        )

        return (
            f"The action failed to move any emails because the provided destination "
            "folder was not found in the following mailbox(es):\n"
            f"{failed_folder_mailboxes}: {self.params.destination_folder}"
        )

    @property
    def _no_mailbox_err_msg(self) -> str:
        if not self.results.failed_mailboxes:
            return ""

        failed_mailboxes = convert_list_to_comma_string(self.results.failed_mailboxes)

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

    mailbox_to_email_ids = defaultdict(list)
    for email in emails:
        email.cleanup_not_required_keys()
        mailbox_to_email_ids[email.mailbox_name].append(email.to_json())

    for mailbox, email_ids in mailbox_to_email_ids.items():
        mailbox_data[mailbox] = email_ids


def _get_common_valid_mailboxes(
    src_mailboxes: Iterable[MicrosoftGraphFolder],
    dst_mailboxes: Iterable[MicrosoftGraphFolder],
) -> Iterable[MicrosoftGraphFolder]:
    src_mailboxes_names = {folder.mailbox_name for folder in src_mailboxes}
    dst_mailboxes_names = {folder.mailbox_name for folder in dst_mailboxes}
    valid_mailboxes = src_mailboxes_names & dst_mailboxes_names

    return [
        folder for folder in src_mailboxes if folder.mailbox_name in valid_mailboxes
    ]


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.DELETE_EMAIL_SCRIPT_NAME
    action = MoveEmailAction(siemplify)
    action.run()


if __name__ == "__main__":
    main()

from __future__ import annotations

from collections.abc import Iterable, MutableMapping, MutableSequence
from collections import defaultdict
import dataclasses
from io import StringIO
import json
import os
import pathlib
import datetime
from typing import Any, NoReturn
from core import exceptions
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.transformation import convert_list_to_comma_string
from TIPCommon.types import SingleJson
from TIPCommon.validation import ParameterValidator
from core.AsyncActionBaseClass import ActionResult, AsyncActionBaseClass
from core.MicrosoftGraphMailDelegatedManager import ApiManager
from core import constants
from core.datamodels import (
    MicrosoftGraphEmail,
    MicrosoftGraphFolder,
    MicrosoftGraphAttachment,
)
from core import utils


@dataclasses.dataclass(slots=True)
class ActionData:
    processed_mailboxes: MutableMapping[str, str]
    pending_mailboxes: MutableSequence[str]
    failed_mailboxes: MutableSequence[str]
    failed_folder_mailboxes: MutableSequence[str]
    downloaded_attachments: MutableSequence[str]
    email_with_no_attachments: MutableSequence[str]
    processed_mail_ids: MutableSequence[str]

    @classmethod
    def from_json(cls, json_data: MutableMapping[str, str]) -> ActionData:
        return cls(
            processed_mailboxes=json_data["processed_mailboxes"],
            pending_mailboxes=json_data["pending_mailboxes"],
            failed_mailboxes=json_data["failed_mailboxes"],
            failed_folder_mailboxes=json_data["failed_folder_mailboxes"],
            downloaded_attachments=json_data["downloaded_attachments"],
            email_with_no_attachments=json_data["email_with_no_attachments"],
            processed_mail_ids=json_data["processed_mail_ids"],
        )


class DownloadAttachmentsFromEmailAction(AsyncActionBaseClass):

    def __init__(self, siemplify):
        super().__init__(siemplify)
        self.results = ActionData(
            processed_mailboxes={},
            pending_mailboxes=[],
            failed_mailboxes=[],
            failed_folder_mailboxes=[],
            downloaded_attachments=[],
            email_with_no_attachments=[],
            processed_mail_ids=[],
        )

    def _extract_action_configuration(self) -> None:
        self.params.mailbox = extract_action_param(
            siemplify=self.siemplify,
            param_name="Search In Mailbox",
            is_mandatory=True,
            default_value=constants.DEFAULT_MAILBOX,
            print_value=True,
        )
        self.params.mailbox = string_to_multi_value(
            self.params.mailbox,
            only_unique=True,
        )
        self.params.folder_name = extract_action_param(
            siemplify=self.siemplify,
            param_name="Folder Name",
            default_value="Inbox",
            print_value=True,
        )
        self.params.download_destination = extract_action_param(
            siemplify=self.siemplify,
            param_name="Download Destination",
            default_value="GCP Bucket",
            is_mandatory=True,
            print_value=True,
        )
        self.params.download_path = extract_action_param(
            siemplify=self.siemplify,
            param_name="Download Path",
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
        self.params.download_from_eml = extract_action_param(
            siemplify=self.siemplify,
            param_name="Download Attachments from EML",
            input_type=bool,
            print_value=True,
        )
        self.params.download_to_unique_path = extract_action_param(
            siemplify=self.siemplify,
            param_name="Download Attachments to unique path?",
            input_type=bool,
            print_value=True,
        )
        self.params.batch = extract_action_param(
            siemplify=self.siemplify,
            param_name="How many mailboxes to process in a single batch",
            is_mandatory=False,
            default_value=constants.DEFAULT_BATCH_SIZE,
            input_type=int,
        )
        self.params.additional_data = extract_action_param(
            siemplify=self.siemplify,
            param_name="additional_data",
            default_value="{}",
        )

    def _validate_params(self, validator: ParameterValidator) -> None:
        validator.validate_ddl(
            param_name="Download Destination",
            value=self.params.download_destination,
            ddl_values=constants.DOWNLOAD_DESTINATION,
            case_sensitive=True,
        )
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
            validator.validate_email(param_name="Search In Mailbox", email=email)

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

        batch = self._get_mailboxes_batch()
        self.logger.info(f"Processing {len(batch)} mailboxes.")
        mailboxes = utils.get_mailboxes_result(
            manager=manager,
            mailboxes=batch,
            folder_name=self.params.folder_name,
        )
        self._validate_mailbox_result(mailboxes)
        emails = self._get_emails_to_download_attachments(
            manager=manager,
            mailboxes=mailboxes.valid_mailboxes,
        )
        emails = utils.get_emails_with_updated_metadata(
            manager=manager,
            emails=emails,
            smime_auth=self.params.smime_auth,
        )

        email_attachment_list = self._get_attachments(
            manager=manager,
            email_attachments_to_download=emails,
        )

        downloaded_attachments = self._download_attachments(
            manager=manager,
            attachments_to_download=email_attachment_list,
            path=self.params.download_path,
            download_from_eml=self.params.download_from_eml,
        )

        self._set_action_result(
            mailboxes=mailboxes,
            emails=emails,
            downloaded_attachments=downloaded_attachments,
        )
        self._set_json_result()
        self._log_messages()

        return self._finalize_action()

    def _set_action_data(self, manager: ApiManager) -> None:
        """Set mailbox data into the results attribute. If it's first run set all
            mailboxes to pending_mailboxes in result attribute otherwise
            additional data from async run.

        Args:
            valid_mailboxes (list[str]): A list of mailboxes that are searchable.
            invalid_mailboxes (list[str]): A list of mailboxes that are
                unsearchable.
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

    def _validate_mailbox_result(self, mailbox_result: utils.MailboxResult) -> None:
        if set(mailbox_result.invalid_mailboxes) == set(self.params.mailbox):
            raise exceptions.MailboxNotFoundException(
                f'The provided mailbox "{self.params.mailbox}" was not found.'
            )

        if mailbox_result.invalid_folder_mailboxes:
            mailboxes_str = ", ".join(mailbox_result.invalid_folder_mailboxes)
            raise exceptions.FolderNotFoundException(
                "The action failed to run because the provided mailbox folder name "
                f'"{self.params.folder_name}" was not found in the mailboxes \n'
                f"{mailboxes_str}"
            )

    def _get_emails_to_download_attachments(
        self,
        manager: ApiManager,
        mailboxes: Iterable[MicrosoftGraphFolder],
    ) -> Iterable[MicrosoftGraphEmail]:
        if not self.params.mail_ids:
            mailboxes = utils.update_search_filters(
                folders=mailboxes,
                subject_filter=self.params.subject_filter,
                sender_filter=self.params.sender_filter,
            )

            return manager.search_emails(mailboxes)

        emails_from_mail_ids = utils.get_emails_with_email_ids(
            manager=manager,
            mailboxes=mailboxes,
            email_ids=self.params.mail_ids,
        )
        self.results.processed_mail_ids.extend(
            [
                (
                    email.id
                    if email.id in self.params.mail_ids
                    else email.internet_message_id
                )
                for email in emails_from_mail_ids
            ]
        )

        return emails_from_mail_ids

    def _get_attachments(
        self,
        manager: ApiManager,
        email_attachments_to_download: Iterable[MicrosoftGraphEmail],
    ) -> Iterable[MicrosoftGraphAttachment]:
        """
        Downloads and returns a list of email attachment objects from
        the Microsoft Graph API.

        Args:
            email_attachments_to_download (Iterable[MicrosoftGraphEmail]): A list of
            MicrosoftGraphEmail objects of emails with attachments to be downloaded.

        Returns:
            Iterable[MicrosoftGraphAttachment]: A list of MicrosoftGraphAttachment
            objects containing downloaded attachments.
        """
        attachments: list[MicrosoftGraphAttachment] = []
        for email in email_attachments_to_download:
            if not email.has_attachments:
                if email.internet_message_id in self.params.mail_ids:
                    self.results.email_with_no_attachments.append(
                        email.internet_message_id
                    )
                else:
                    self.results.email_with_no_attachments.append(email.id)
                continue

            email_attachments = utils.get_attachments(manager=manager, email=email)
            attachments.extend(email_attachments)

        return attachments

    def _download_attachments(
        self,
        manager: ApiManager,
        attachments_to_download: Iterable[MicrosoftGraphAttachment],
        download_from_eml: bool,
        path: str,
    ) -> list[MutableMapping[str, str]]:
        attachment_details: list[MutableMapping[str, str]] = []

        if not attachments_to_download:
            return []

        resolved_path: str = self._create_and_resolve_download_path(path)

        for attachment in attachments_to_download:
            attachment_data = self._get_attachment_data(
                manager=manager,
                attachment=attachment,
                download_from_eml=download_from_eml,
                path=resolved_path,
            )
            attachment_details.extend(attachment_data)

        if not attachment_details:
            return []

        if self._is_local_destination:
            return [
                self.save_attachment_locally(attachment)
                for attachment in attachment_details
            ]

        if self._is_gcp_destination:
            return [
                self.save_attachment_to_gcp(attachment)
                for attachment in attachment_details
            ]

        return []

    def _get_attachment_data(
        self,
        manager: ApiManager,
        attachment: MicrosoftGraphAttachment,
        download_from_eml: bool,
        path: str,
    ) -> Iterable[MutableMapping[str, str]]:
        if not attachment.is_smime:
            return manager.download_attachment_from_email(
                attachment=attachment,
                download_from_eml=download_from_eml,
                path=path,
                smime_auth=self.params.smime_auth,
            )

        return self._get_smime_attachment_data(
            manager=manager,
            attachment=attachment,
            download_from_eml=download_from_eml,
            path=path,
        )

    def _get_smime_attachment_data(
        self,
        manager: ApiManager,
        attachment: MicrosoftGraphAttachment,
        download_from_eml: bool,
        path: str,
    ) -> Iterable[MutableMapping[str, str]]:
        attachment_data = [
            {
                "attachment_name": attachment.name,
                "attachment_content": attachment.content_bytes,
                "path": path,
            }
        ]
        if download_from_eml:
            attachment_data.extend(
                manager.get_attachment_from_eml(
                    attachment_content=attachment.content_bytes,
                    path=path,
                )
            )

        return attachment_data

    def save_attachment_locally(
        self,
        attachment_values: MutableMapping[str, str],
    ) -> MutableMapping[str, str]:
        """Saves an attachment locally based on the provided information.

        Args:
            attachment_values (MutableMapping[str, str]): A dictionary containing
            attachment details, expected to have keys 'attachment_name',
            'attachment_content' and 'path'.

        Returns:
            MutableMapping[str, str]: A dictionary containing file_name, path of the
            saved attachment, as returned by the `save_attachment_to_local` function.
        """
        attachment_name, attachment_content, path = attachment_values.values()

        return self.save_attachment_to_local(
            unique_path=self.params.download_to_unique_path,
            attachment_name=attachment_name,
            attachment_content=attachment_content,
            path=path,
        )

    def save_attachment_to_gcp(
        self,
        attachment_values: MutableMapping[str, str],
    ) -> MutableMapping[str, str]:
        """Saves an attachment on gcp based on the provided information.

        Args:
            attachment_values (MutableMapping[str, str]): A dictionary containing
            attachment details, expected to have keys 'attachment_name',
            'attachment_content' and 'path'.

        Returns:
            MutableMapping[str, str]: A dictionary containing file_name, path of the
            saved attachment.
        """
        downloaded_gcp_attachment: MutableMapping[str, str] = {}
        attachment_name, attachment_content, path = attachment_values.values()
        try:
            downloaded_gcp_attachment = {
                "attachment_name": attachment_name,
                "downloaded_path": utils.save_file_to_gcp(
                    file_path=path,
                    chronicle_soar=self.siemplify,
                    file_name=attachment_name,
                    file_content=attachment_content,
                ),
            }

        except FileNotFoundError:
            self._create_and_resolve_download_path(path)

            downloaded_gcp_attachment = {
                "attachment_name": attachment_name,
                "downloaded_path": utils.save_file_to_gcp(
                    file_path=path,
                    chronicle_soar=self.siemplify,
                    file_name=attachment_name,
                    file_content=attachment_content,
                ),
            }

        return downloaded_gcp_attachment

    def _create_and_resolve_download_path(self, path: str) -> str:
        resolved_path = self._resolve_download_path(path)
        path_obj = pathlib.Path(resolved_path)

        if not path_obj.exists():
            path_obj.mkdir(parents=True)
            self.logger.info(
                f"Created new folder for downloading email attachments: {resolved_path}"
            )

        return resolved_path


    def _resolve_download_path(self, path: str) -> str:
        path_obj = pathlib.Path(path)
        if not path_obj.is_absolute():
            path_obj = pathlib.Path(self.siemplify.RUN_FOLDER) / path

        return str(path_obj)

    def save_attachment_to_local(
        self,
        unique_path: bool,
        attachment_name: str,
        attachment_content: str,
        path: str,
    ) -> MutableMapping[str, str] | None:
        """Download Attachments to local path in file system for Microsoft Graph email
        attachments from provided Attachment data object.

        Args:
            attachments_content: Content of attachment to save in destination
            download_destination: local or on gcp
            path: Path on the server where to download the email attachments
            attachment_name: Name of attachment to save in destination
            unique_path: Specify whether download attachments to unique path or no

        Returns:
            MutableMapping[str, str] Dictionary of Saved Attachment Detail
        """
        attachment_name = utils.fix_filename(attachment_name)
        attachment_local_name = None
        if isinstance(attachment_content, type(None)):
            return None

        if unique_path:
            attachment_local_name = self.build_attachment_unique_name(attachment_name)

        local_path = pathlib.Path(path) / (attachment_local_name or attachment_name)
        local_path.write_bytes(attachment_content)

        return {"attachment_name": attachment_name, "downloaded_path": str(local_path)}

    def build_attachment_unique_name(self, attachment_name: str) -> str:
        """
        Build unique attachment name based on attachment name
        Args:
            attachment_name: {str}  Original attachment name
        Returns:
            {str} unique attachment name.
            Format:"{original_name}-{timestamp}{extension}".
        """
        name, extension = os.path.splitext(attachment_name)
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S_%f")[:-3]
        return f"{name}-{timestamp}{extension}"

    def _set_action_result(
        self,
        mailboxes: utils.MailboxResult,
        emails: Iterable[MicrosoftGraphEmail],
        downloaded_attachments: MutableSequence[MutableMapping[str, str]],
    ) -> None:
        """Set the result of pending, processed and failed mailboxes.

        Args:
            mailboxes (MailboxResult): The result of processing mailboxes.
            emails (Iterable[MicrosoftGraphEmail]): List of searched emails.
            downloaded_attachment(MutableSequence[MutableMapping[str, str]]: List of
            downloaded attachments.
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
        self.results.downloaded_attachments.extend(downloaded_attachments)

    def _set_json_result(self) -> None:
        """Add json result to the case."""
        json_result_emails = [
            {
                "attachment_name": attachment["attachment_name"],
                "downloaded_path": attachment["downloaded_path"],
            }
            for attachment in self.results.downloaded_attachments
        ]

        self.siemplify.result.add_result_json(json_result_emails)

    def _log_messages(self) -> None:
        self.logger.info(self._all_searched_emails_msg)

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

        if not self.results.downloaded_attachments:
            return self._finalize_action_on_failure()

        return self._finalize_action_on_success()

    def _finalize_action_on_timeout(self) -> ActionResult:
        has_processed_emails = utils.has_processed_emails(
            self.results.processed_mailboxes
        )
        if self.results.processed_mailboxes and has_processed_emails:
            self.output_messages.append(self._timeout_with_success_msg)
            self.output_messages.append(self._mailbox_err_msg)
            self.output_messages.append(self._folder_err_msg)

            return ActionResult(ExecutionState.TIMED_OUT, True)

        message = "Action failed to download attachments until timeout."
        self.output_messages.append(message)

        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_inprogress(self) -> ActionResult:
        message: str = (
            f"Mailboxes processed: {len(self.results.processed_mailboxes)}. "
            "Continuing..."
        )
        self.output_messages.append(message)
        self.results.processed_mail_ids = list(set(self.results.processed_mail_ids))
        return ActionResult(
            ExecutionState.IN_PROGRESS,
            json.dumps(dataclasses.asdict(self.results)),
        )

    def _finalize_action_on_failure(self) -> ActionResult:
        all_failed_mailboxes = set(self.results.failed_mailboxes) == set(
            self.params.mailbox
        )
        if all_failed_mailboxes:
            self.output_messages.append(self._no_mailbox_err_msg)

            return ActionResult(ExecutionState.FAILED, False)

        if self.results.failed_folder_mailboxes:
            self.output_messages.append(self._failure_folder_err_msg)

            return ActionResult(ExecutionState.FAILED, False)

        if self.params.mail_ids:
            all_invalid_mail_ids = set(self.params.mail_ids) - (
                set(self.results.processed_mail_ids)
                | set(self.results.email_with_no_attachments)
            )
            if len(all_invalid_mail_ids) == len(set(self.params.mail_ids)):
                self.output_messages.append(self._failure_mail_id_err_msg)

                return ActionResult(ExecutionState.FAILED, False)

        if not all_failed_mailboxes:
            self.output_messages.append(self._success_without_emails_msg)
            self.output_messages.append(self._mailbox_err_msg)
            self.output_messages.append(self._folder_err_msg)

            return ActionResult(ExecutionState.COMPLETED, False)

        self.output_messages.append("Action Failed")

        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_success(self) -> ActionResult:
        self.output_messages.append(self._success_with_emails_msg)
        self.output_messages.append(self._success_without_emails_msg)
        self.output_messages.append(self._mailbox_err_msg)
        self.output_messages.append(self._folder_err_msg)
        failed_ids = []
        if self.params.mail_ids:
            failed_ids = self._failed_mail_ids()

        if failed_ids or self.results.email_with_no_attachments:
            return ActionResult(ExecutionState.COMPLETED, False)

        return ActionResult(ExecutionState.COMPLETED, True)

    def _failed_mail_ids(self) -> MutableSequence[str]:
        failed_ids: set[str] = set()
        processed_mails: MutableSequence[str] = []
        for mails in self.results.processed_mailboxes.values():
            processed_mails.extend([mail["id"] for mail in mails])
            processed_mails.extend([mail["internetMessageId"] for mail in mails])
        if self.params.mail_ids:
            failed_ids = set(self.params.mail_ids) - set(processed_mails)

        return list(failed_ids) or []

    @property
    def _all_searched_emails_msg(self) -> str:
        message: str = (
            "Searched emails with provided search criteria to download attachments:"
        )
        for mailbox, emails in self.results.processed_mailboxes.items():
            message += f"\n{mailbox}: {len(emails)}"

        return message

    @property
    def _success_with_emails_msg(self) -> str:
        message: str = (
            "Successfully downloaded attachments found in emails in "
            "the following mailboxes: \n"
        )

        message += "\n".join(mailbox for mailbox in self.results.processed_mailboxes)

        message += (
            f"\n\nDownloaded {len(self.results.downloaded_attachments)} attachments."
        )

        containing_dir: str = self._resolve_download_path(self.params.download_path)

        message += f"\nContaining Directory: {containing_dir}\n\nFiles:"

        for attachment in self.results.downloaded_attachments:
            message += (
                f"\n{attachment['attachment_name']}: {attachment['downloaded_path']}"
            )

        if len(self.results.downloaded_attachments) == 0:
            message = ""

        return message

    @property
    def _success_without_emails_msg(self) -> str:
        message: str = ""
        if not self.params.mail_ids:
            if self.results.email_with_no_attachments:
                message += self._mailbox_with_no_attachment_email_msg
            elif not self.results.downloaded_attachments:
                message += "Failed to find any emails using the provided criteria!"

            return message

        processed_mails = []
        for mails in self.results.processed_mailboxes.values():
            processed_mails.extend([mail["id"] for mail in mails])
            processed_mails.extend([mail["internetMessageId"] for mail in mails])
        failed_mails = set(self.params.mail_ids) - (
            set(processed_mails) - set(self.results.email_with_no_attachments)
        )
        mails_found_but_no_attachment = failed_mails & set(
            self.results.email_with_no_attachments
        )
        mails_not_processed_at_all = failed_mails - mails_found_but_no_attachment
        if not failed_mails:
            return ""

        if mails_found_but_no_attachment:
            message += self._mailbox_with_no_attachment_email_msg

        if mails_not_processed_at_all:
            failed_mails_str = "\n".join(mails_not_processed_at_all)
            message += (
                f"Failed to find emails with following mail ids:\n{failed_mails_str}\n"
            )

        return message

    @property
    def _timeout_with_success_msg(self) -> str:
        processed_mailboxes_str: str = convert_list_to_comma_string(
            list(self.results.processed_mailboxes.keys()),
            delimiter=", ",
        )
        pending_mailboxes_str: str = convert_list_to_comma_string(
            self.results.pending_mailboxes,
            delimiter=", ",
        )
        return (
            "The action ran into a timeout during execution.\n"
            f"Processed mailboxes: {processed_mailboxes_str}\n"
            f"Pending mailboxes: {pending_mailboxes_str}\n"
            "Please increase the timeout in IDE."
        )

    @property
    def _timeout_with_failure_msg(self) -> str:
        return "The action failed to download any attachments until timeout."

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
            self.results.failed_folder_mailboxes,
            delimiter=", ",
        )

        return (
            "The action failed to search any emails because the "
            "provided mailbox folder name was not found in the mailbox(es):\n"
            f"{failed_folder_mailboxes}: {self.params.folder_name}"
        )

    @property
    def _failure_mail_id_err_msg(self) -> str:
        return "Failed to find any emails using the provided criteria!"

    @property
    def _failure_folder_err_msg(self) -> str:
        if not self.results.failed_folder_mailboxes:
            return ""

        failed_folder_mailboxes: str = convert_list_to_comma_string(
            self.results.failed_folder_mailboxes,
            delimiter=", ",
        )

        return (
            "Action failed to run because the provided mailbox folder name "
            "was not found in the mailbox(es):\n"
            f"{failed_folder_mailboxes}: {self.params.folder_name}"
        )

    @property
    def _no_mailbox_err_msg(self) -> str:
        if not self.results.failed_mailboxes:
            return ""

        failed_mailboxes: str = convert_list_to_comma_string(
            self.results.failed_mailboxes
        )

        return f"Failed to find any of the provided mailboxes:\n {failed_mailboxes}"

    @property
    def _mailbox_with_no_attachment_email_msg(self) -> str:
        msg_bfr = StringIO()
        msg_bfr.write(
            "The action didn't find any attachments for emails in provided mailboxes."
            "\nAffected mailboxes:\n"
        )
        found_mailboxes = set()
        for mailbox, mailboxes_data in self.results.processed_mailboxes.items():
            for mailbox_data in mailboxes_data:
                if (
                    mailbox_data["id"]
                    or mailbox_data["internetMessageId"]
                    in self.results.email_with_no_attachments
                ):
                    if mailbox not in found_mailboxes:
                        msg_bfr.write(f"{mailbox}\n")
                        found_mailboxes.add(mailbox)

        msg_bfr.write("\nMail ids without attachments to download:\n")
        mails_str = "\n".join(set(self.results.email_with_no_attachments))
        msg_bfr.write(f"{mails_str}\n\n")
        message = msg_bfr.getvalue()
        msg_bfr.close()
        return message

    @property
    def _is_local_destination(self) -> bool:
        return bool(self.params.download_destination == "Local File System")

    @property
    def _is_gcp_destination(self) -> bool:
        return bool(self.params.download_destination == "GCP Bucket")


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
        mailbox_data (SingleJson): A dictionary to be updated with mailbox names as keys
        and lists of associated email IDs.
    """

    mailbox_to_email_ids: defaultdict[str, list[Any]] = defaultdict(list)
    for email in emails:
        email.cleanup_not_required_keys()
        mailbox_to_email_ids[email.mailbox_name].append(email.to_json())

    for mailbox, email_ids in mailbox_to_email_ids.items():
        mailbox_data[mailbox] = email_ids


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.DOWNLOAD_ATTACHMENTS_FROM_EMAIL
    action = DownloadAttachmentsFromEmailAction(siemplify)
    action.run()


if __name__ == "__main__":
    main()

from __future__ import annotations

from typing import NoReturn

from collections.abc import Iterable, MutableMapping, MutableSequence

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from TIPCommon.validation import ParameterValidator
from core import action_init
from core import constants
from core.datamodels import MicrosoftGraphEmail, MicrosoftGraphFolder
from core import exceptions
from core import utils
from core import MicrosoftGraphMailDelegatedManager as api_manager


def _mark_emails_as_not_junk(
    manager: api_manager.ApiManager,
    emails_to_mark_as_not_junk: Iterable[MicrosoftGraphEmail],
) -> None:
    for email in emails_to_mark_as_not_junk:
        manager.mark_email_as_not_junk(email)


class MarkEmailAsNotJunk(Action[api_manager.ApiManager]):

    def __init__(self) -> None:
        super().__init__(constants.MARK_EMAIL_AS_NOT_JUNK_SCRIPT_NAME)
        self.output_message = "Successfully marked the email as not junk.\n\n"
        self.error_output_message = (
            f'Error executing action "{constants.MARK_EMAIL_AS_NOT_JUNK_SCRIPT_NAME}".'
        )

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _extract_action_parameters(self) -> None:
        self.params.mailboxes = extract_action_param(
            self.soar_action,
            param_name="Search In Mailbox",
            default_value=constants.DEFAULT_MAILBOX,
            is_mandatory=True,
            print_value=True,
        )
        self.params.mailboxes = string_to_multi_value(
            self.params.mailboxes,
            only_unique=True,
        )
        self.params.folder_name = extract_action_param(
            self.soar_action,
            param_name="Folder Name",
            default_value=constants.DEFAULT_JUNK_FOLDER_NAME,
            is_mandatory=True,
            print_value=True,
        )
        self.params.mail_ids = extract_action_param(
            self.soar_action,
            param_name="Mail IDs",
            is_mandatory=True,
            print_value=True,
        )
        self.params.mail_ids = string_to_multi_value(
            self.params.mail_ids,
            only_unique=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        for email in self.params.mailboxes:
            email = (
                self.api_client.mail_address
                if email == constants.DEFAULT_MAILBOX
                else email
            )
            validator.validate_email(param_name="Search In Mailbox", email=email)

    def _perform_action(self, _) -> None:
        valid_mailboxes, invalid_mailboxes = utils.filter_valid_invalid_mailboxes(
            manager=self.api_client,
            mailboxes=self.params.mailboxes,
            default_mailbox=self.api_client.mail_address,
        )
        mailbox_result = utils.get_mailboxes_result(
            manager=self.api_client,
            mailboxes=valid_mailboxes,
            folder_name=self.params.folder_name,
        )
        self._validate_mailbox_result(mailbox_result, invalid_mailboxes)
        emails_to_mark_as_not_junk = self._get_validated_emails(
            folders=mailbox_result.valid_mailboxes
        )
        _mark_emails_as_not_junk(
            manager=self.api_client,
            emails_to_mark_as_not_junk=emails_to_mark_as_not_junk,
        )

    def _validate_mailbox_result(
        self,
        mailbox_result: utils.MailboxResult,
        invalid_mailboxes: Iterable[str],
    ) -> None:
        mailboxes_str = convert_list_to_comma_string(self.params.mailboxes)
        if invalid_mailboxes and not mailbox_result.valid_mailboxes:
            raise exceptions.MailboxNotFoundException(
                "Failed to find any of the provided mailboxes:\n " f'"{mailboxes_str}"'
            )

        if invalid_mailboxes and mailbox_result.valid_mailboxes:
            self.output_message += (
                "The provided mailbox "
                f'"{convert_list_to_comma_string(invalid_mailboxes)}" '
                "was not found.\n\n"
            )

        if mailbox_result.invalid_folder_mailboxes:
            raise exceptions.FolderNotFoundException(
                "The action failed to run because the provided mailbox folder name "
                f'"{self.params.folder_name}" was not found in the mailbox/es '
                f'"{mailboxes_str}"'
            )

    def _get_validated_emails(
        self,
        folders: Iterable[MicrosoftGraphFolder],
    ) -> MutableMapping[str, MutableSequence[MicrosoftGraphEmail]]:
        emails = utils.get_emails_with_email_ids(
            manager=self.api_client,
            mailboxes=folders,
            email_ids=self.params.mail_ids,
        )
        valid_ids = {email.id for email in emails} | {
            email.internet_message_id for email in emails
        }
        invalid_mail_ids: set[str] = set(self.params.mail_ids) - valid_ids
        invalid_ids_str: str = convert_list_to_comma_string(list(invalid_mail_ids))
        mailbox: str = convert_list_to_comma_string(self.params.mailboxes)

        if not valid_ids and invalid_mail_ids:
            raise exceptions.InvalidParameterException(
                "Failed to find any emails based on provided parameters!"
            )

        if invalid_mail_ids and valid_ids:
            self.output_message += (
                f'Failed to find email with the ID "{invalid_ids_str}" in'
                f' "{mailbox}".\n\n'
            )

        return emails


def main() -> NoReturn:
    action = MarkEmailAsNotJunk()
    action.run()


if __name__ == "__main__":
    main()

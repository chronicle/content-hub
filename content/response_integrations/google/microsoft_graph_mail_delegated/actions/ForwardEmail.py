from __future__ import annotations

from typing import NoReturn
from collections.abc import MutableMapping, MutableSequence

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from core import action_init
from core import constants
from core.datamodels import MicrosoftGraphEmail, MicrosoftGraphFolder
from core import exceptions
from core import utils
from core import MicrosoftGraphMailDelegatedManager as api_manager


class ForwardEmailAction(Action[api_manager.ApiManager]):

    def __init__(self) -> None:
        super().__init__(constants.FORWARD_EMAIL_SCRIPT_NAME)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{constants.FORWARD_EMAIL_SCRIPT_NAME}".'
        )
        self.result_value = True
        self.json_results = {}

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _extract_action_parameters(self) -> None:
        self.params.send_from = extract_action_param(
            self.soar_action,
            param_name="Send From",
            default_value=constants.DEFAULT_MAILBOX,
            is_mandatory=True,
            input_type=str,
            print_value=True,
        )
        self.params.email_id = extract_action_param(
            self.soar_action,
            param_name="Mail ID",
            is_mandatory=True,
            input_type=str,
            print_value=True,
        )
        self.params.send_to = extract_action_param(
            self.soar_action,
            param_name="Send to",
            is_mandatory=True,
            input_type=str,
            print_value=True,
        )
        self.params.send_to = string_to_multi_value(
            self.params.send_to,
            only_unique=True,
        )
        self.params.subject = extract_action_param(
            self.soar_action,
            param_name="Subject",
            is_mandatory=True,
            input_type=str,
            print_value=True,
        )
        self.params.folder_name = extract_action_param(
            self.soar_action,
            param_name="Folder Name",
            default_value=constants.DEFAULT_FOLDER_NAME,
            is_mandatory=False,
            input_type=str,
            print_value=True,
        )
        self.params.attachments_paths = extract_action_param(
            self.soar_action,
            param_name="Attachments Paths",
            is_mandatory=False,
            input_type=str,
            print_value=True,
        )
        self.params.attachments_paths = string_to_multi_value(
            self.params.attachments_paths,
            only_unique=True,
        )
        self.params.mail_content = extract_action_param(
            self.soar_action,
            param_name="Mail Content",
            is_mandatory=True,
            input_type=str,
            print_value=True,
        )
        self.params.cc = extract_action_param(
            self.soar_action,
            param_name="CC",
            is_mandatory=False,
            input_type=str,
            print_value=True,
        )
        self.params.cc = string_to_multi_value(self.params.cc, only_unique=True)
        self.params.bcc = extract_action_param(
            self.soar_action,
            param_name="BCC",
            is_mandatory=False,
            input_type=str,
            print_value=True,
        )
        self.params.attachment_location = extract_action_param(
            self.soar_action,
            param_name="Attachment Location",
            default_value="GCP Bucket",
            is_mandatory=True,
            print_value=True,
        )
        self.params.bcc = string_to_multi_value(self.params.bcc, only_unique=True)

    def _validate_params(self) -> None:
        invalid_paths: MutableSequence[str] = []
        invalid_paths = [
            file_path
            for file_path in self.params.attachments_paths
            if not utils.validate_file(
                chronicle_soar=self.soar_action,
                file_identifier=file_path,
                file_location=self.params.attachment_location,
            )
        ]

        if invalid_paths:
            invalid_paths = convert_list_to_comma_string(invalid_paths, delimiter=", ")
            error_message = (
                "The action failed to run because the specified attachments were not "
                f"found: {invalid_paths}"
            )
            raise exceptions.InvalidAttachmentPathException(error_message)

    def _perform_action(self, _) -> None:
        self._set_mailbox()
        mailbox_result = utils.get_mailboxes_result(
            manager=self.api_client,
            mailboxes=[self.params.send_from],
            folder_name=self.params.folder_name,
        )
        self._validate_mailbox_result(mailbox_result=mailbox_result)
        email = self._validate_email_id(folder=mailbox_result.valid_mailboxes[0])
        forward_email = self._forward_email(email)
        sent_folder = self._get_sent_folder()
        forwarded_email = _get_forwarded_draft_email(
            manager=self.api_client,
            folder=sent_folder,
            email=forward_email,
            timeout_in_ms=self.soar_action.execution_deadline_unix_time_ms,
        )
        self._set_action_result(forwarded_email)

    def _set_mailbox(self) -> None:
        self.params.send_from = utils.validate_mailbox(
            manager=self.api_client,
            mailbox=self.params.send_from,
            default_mailbox=self.api_client.mail_address,
        )

    def _validate_mailbox_result(self, mailbox_result: utils.MailboxResult) -> None:
        if mailbox_result.invalid_mailboxes:
            raise exceptions.MailboxNotFoundException(
                f'The provided mailbox "{self.params.send_from}" was not found.'
            )
        if mailbox_result.invalid_folder_mailboxes:
            raise exceptions.FolderNotFoundException(
                f'The provided folder name "{self.params.folder_name}" was not found.'
            )

    def _validate_email_id(self, folder: MicrosoftGraphFolder) -> MicrosoftGraphEmail:
        try:
            return self.api_client.get_mail_details(
                folder=folder,
                email_id=self.params.email_id,
            )

        except exceptions.MicrosoftGraphMailManagerError as error:
            raise exceptions.InvalidParameterException(
                f"The provided mail ID {self.params.email_id} was not found."
            ) from error

    def _forward_email(self, email: MicrosoftGraphEmail) -> MicrosoftGraphEmail:
        return self.api_client.forward_email(
            send_from=self.params.send_from,
            email_id=email.id,
            subject=self.params.subject,
            send_to=self.params.send_to,
            mail_content=self.params.mail_content,
            cc=self.params.cc,
            bcc=self.params.bcc,
            attachments_data=self._get_attachment_data(),
        )

    def _get_attachment_data(self) -> MutableSequence[MutableMapping[str, str]]:
        return [
            utils.load_attachment(
                chronicle_soar=self.soar_action,
                attachment_path=attachment_path,
                attachment_location=self.params.attachment_location,
            )
            for attachment_path in self.params.attachments_paths
        ]

    def _get_sent_folder(self) -> MicrosoftGraphFolder:
        return self.api_client.get_folder_by_name(
            folder_name=constants.DEFAULT_SENT_FOLDER_NAME,
            mail_address=self.params.send_from,
        )

    def _set_action_result(self, email: MicrosoftGraphEmail) -> None:
        email.cleanup_not_required_keys()
        self.json_results = email.to_json()
        self.output_message = (
            f"The email with the mail ID {self.params.email_id} was forwarded "
            "successfully."
        )


def _get_forwarded_draft_email(
    manager: api_manager.ApiManager,
    folder: MicrosoftGraphFolder,
    email: MicrosoftGraphEmail,
    timeout_in_ms: int,
) -> MicrosoftGraphEmail:
    return utils.get_sent_draft_email(
        manager=manager,
        folder=folder,
        email=email,
        timeout_in_ms=timeout_in_ms,
    )


def main() -> NoReturn:
    action = ForwardEmailAction()
    action.run()


if __name__ == "__main__":
    main()

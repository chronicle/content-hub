from __future__ import annotations

from typing import NoReturn

from collections import namedtuple
from collections.abc import MutableSequence

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.rest import soar_api
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from core import action_init
from core import constants
from core.datamodels import (
    MicrosoftGraphAttachment,
    MicrosoftGraphEmail,
    MicrosoftGraphFolder,
)
from core.exceptions import MicrosoftGraphMailManagerError
from core import utils
from core import MicrosoftGraphMailDelegatedManager as api_manager


EmailAndEMLContent = namedtuple("EmailAndEMLContent", ["email", "email_as_eml"])
AttachmentsResult = namedtuple(
    "AttachmentsResult", ["attachments", "attachments_not_found"]
)


class SaveEmailToCase(Action[api_manager.ApiManager]):

    def __init__(self) -> None:
        super().__init__(constants.SAVE_EMAIL_TO_CASE_SCRIPT_NAME)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{constants.SAVE_EMAIL_TO_CASE_SCRIPT_NAME}".'
        )
        self.json_results = {}
        self.result_value = True
        self.attachments_not_found = []
        self.attachments_saved = []

    def _extract_action_parameters(self) -> None:
        self.params.smime_auth = utils.get_integration_parameters(
            self.soar_action
        ).smime_auth
        self.params.mailbox = extract_action_param(
            self.soar_action,
            param_name="Search In Mailbox",
            default_value=constants.DEFAULT_MAILBOX,
            is_mandatory=True,
            print_value=True,
        )
        self.params.folder_name = extract_action_param(
            self.soar_action,
            param_name="Folder Name",
            default_value=constants.DEFAULT_FOLDER_NAME,
            print_value=True,
        )
        self.params.email_id = extract_action_param(
            self.soar_action,
            param_name="Mail ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.save_only_attachment = extract_action_param(
            self.soar_action,
            param_name="Save Only Email Attachments",
            input_type=bool,
            print_value=True,
        )
        self.params.attachments_to_save = extract_action_param(
            self.soar_action,
            param_name="Attachment To Save",
            print_value=True,
        )
        self.params.base64_encode = extract_action_param(
            self.soar_action,
            param_name="Base64 Encode",
            input_type=bool,
            default_value=False,
            print_value=True,
        )
        self.params.save_email_to_case_wall = extract_action_param(
            self.soar_action,
            param_name="Save Email to the Case Wall",
            input_type=bool,
            default_value=False,
            print_value=True,
        )
        self.params.attachments_to_save = string_to_multi_value(
            self.params.attachments_to_save,
            only_unique=True,
        )

    def _validate_params(self) -> None:
        if "," in self.params.mailbox:
            raise ValueError(
                "MailboxParamValueError: only 1 mailbox is allowed type "
                "csv is not allowed"
            )

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self._set_mailbox()
        folder = self._get_folder_details()
        email_details = self._get_email_and_eml_content(folder)
        if self.params.save_only_attachment:
            attachments_result = self._get_email_attachments(email=email_details.email)
            self._save_attachments_to_case(attachments_result=attachments_result)
        else:
            self._save_email_to_case_result(email_details)

        self._save_email_to_case_wall(email_details)
        self._set_action_result(email_details.email)

    def _set_mailbox(self) -> None:
        self.params.mailbox = utils.validate_mailbox(
            manager=self.api_client,
            mailbox=self.params.mailbox,
            default_mailbox=self.api_client.mail_address,
        )

    def _get_folder_details(self) -> MicrosoftGraphFolder:
        try:
            return self.api_client.get_folder_by_name(
                folder_name=self.params.folder_name,
                mail_address=self.params.mailbox,
            )

        except MicrosoftGraphMailManagerError as error:
            raise MicrosoftGraphMailManagerError(
                self._get_mailbox_folder_error_msg(error)
            ) from error

    def _get_mailbox_folder_error_msg(self, error: Exception):
        if self.params.folder_name in str(error):
            return (
                "The action failed to run because the provided mailbox "
                f'folder name "{self.params.folder_name}" was not found in the '
                f'mailbox "{self.params.mailbox}"'
            )

        return f'The mailbox "{self.params.mailbox}" wasn\'t found.'

    def _get_email_and_eml_content(
        self,
        folder: MicrosoftGraphFolder,
    ) -> EmailAndEMLContent:
        """Get email details and EML content.

        Args:
            folder (MicrosoftGraphFolder): The folder object containing the email

        Returns:
            EmailAndEMLContent: EmailAndEMLContent named tuple the email
            details (MicrosoftGraphEmail) and the EML content (bytes).
        """
        email = self.api_client.get_mail_details(
            folder=folder,
            email_id=self.params.email_id,
        )
        email = utils.get_emails_with_updated_metadata(
            manager=self.api_client,
            emails=[email],
            smime_auth=self.params.smime_auth,
        )[0]
        self.logger.info(
            f'Fetched email with email_id="{self.params.email_id}" in '
            f'folder="{self.params.folder_name}".'
        )
        email_as_eml = (
            email.mime_content
            if email.is_smime_email
            else self.api_client.load_email_content(email)
        )
        email.raw_data["eml_info"] = (
            utils.encode_content_as_base64(item_content=email_as_eml)
            if self.params.base64_encode
            else ""
        )

        return EmailAndEMLContent(
            email,
            utils.encode_content_as_base64(item_content=email_as_eml),
        )

    def _get_email_attachments(self, email: MicrosoftGraphEmail) -> AttachmentsResult:
        if not email.has_attachments:
            return AttachmentsResult([], [])

        attachments = utils.get_attachments(manager=self.api_client, email=email)
        attachments, attachments_not_found = self._filter_attachments(attachments)

        return AttachmentsResult(attachments, attachments_not_found)

    def _filter_attachments(
        self,
        attachments: MutableSequence[MicrosoftGraphAttachment],
    ) -> tuple[MutableSequence[MicrosoftGraphAttachment], MutableSequence[str]]:
        """Filter attachments based on specified attachments_to_save.

        Args:
            attachments MutableSequence[MicrosoftGraphAttachment]: List of attachments
            to filter.

        Returns:
            tuple[MutableSequence[MicrosoftGraphAttachment], MutableSequence[str]]:
            Filtered list of attachments and list of not found attachments in mail.
        """
        attachments_not_found = []
        if not self.params.attachments_to_save:
            return attachments, attachments_not_found

        attachments_in_email = set(self.params.attachments_to_save).intersection(
            a.name for a in attachments
        )
        attachments_not_found = (
            set(self.params.attachments_to_save) - attachments_in_email
        )
        attachments = [
            attachment
            for attachment in attachments
            if attachment.name in attachments_in_email
        ]

        return attachments, list(attachments_not_found)

    def _save_attachments_to_case(self, attachments_result: AttachmentsResult) -> None:
        """Save attachments to the case.

        Args:
            attachments (AttachmentsResult): Attachments object.

        Returns:
            None: This method does not return any value. It updates the
                'result', 'attachments_saved', and 'attachments_not_found'
                attributes of the class instance.
        """
        self.attachments_not_found.extend(attachments_result.attachments_not_found)
        for attachment in attachments_result.attachments:
            try:
                attachment_content = (
                    attachment.content_bytes_as_b64_string
                    if attachment.is_smime
                    else self._get_attachment_content(attachment)
                )
                self._add_attachment(attachment, attachment_content)

            except (MicrosoftGraphMailManagerError, EnvironmentError) as e:
                self.logger.error(
                    f"Unable to save attachment {attachment.name}, Reason: {e}"
                )
                self.attachments_not_found.append(attachment.name)

    def _get_attachment_content(self, attachment: MicrosoftGraphAttachment) -> str:
        """Load and return the content bytes of the attachment."""
        if not attachment.is_item_attachment:
            return attachment.content_bytes

        attachment_content = self.api_client.load_attachment_content(
            folder_id=attachment.folder_id,
            email_id=attachment.email_id,
            attachment_id=attachment.id,
            mail_address=attachment.mailbox_name,
        )

        return utils.encode_content_as_base64(item_content=attachment_content)

    def _add_attachment(
        self,
        attachment: MicrosoftGraphAttachment,
        attachment_content: str,
    ) -> None:
        """Add attachment to the action result.

        Args:
            attachment (MicrosoftGraphAttachment): MicrosoftGraphAttachment object.
            attachment_content (str): Attachment content.
        """
        self.soar_action.result.add_attachment(
            title=f'Email Attachment for "{self.params.email_id}": {attachment.name}',
            filename=attachment.name,
            file_contents=attachment_content,
        )
        self.attachments_saved.append(attachment.name)
        self.logger.info(f'Attachment saved: "{attachment.name}"')

    def _save_email_to_case_result(self, email_details: EmailAndEMLContent) -> None:
        """Save email as eml file to the action result.

        Args:
            email_details (EmailAndEMLContent): namedtuple EmailAndEMLContent object.
        """
        email_subject = email_details.email.subject or constants.EMPTY_EMAIL_SUBJECT
        self.soar_action.result.add_attachment(
            title=email_subject,
            filename=f"{email_subject}.eml",
            file_contents=email_details.email_as_eml,
        )

    def _save_email_to_case_wall(self, email_details: EmailAndEMLContent) -> None:
        email_subject = email_details.email.subject or constants.EMPTY_EMAIL_SUBJECT
        if self.params.save_email_to_case_wall:
            attachment_data = CaseWallAttachment(
                name=email_subject,
                file_type=".eml",
                base64_blob=email_details.email_as_eml,
                is_important=False,
            )

            soar_api.save_attachment_to_case_wall(
                chronicle_soar=self.soar_action, attachment_data=attachment_data
            )

    def _set_action_result(self, email: MicrosoftGraphEmail) -> None:
        """Set the action result based on the provided email and parameters.

        This method performs the following tasks:
        1. Cleanup the email object by removing unnecessary keys.
        2. Set the JSON results for the action.
        3. If the 'save_only_attachment' parameter is False, set the output message
        to the email success message.
        4. If the email does not have any attachments and 'save_only_attachment' is True
            - Set the result value to False.
            - Set the output message to the 'no attachment' message.
        5. If any attachments were saved, set the output message to the 'attachment
            success' message.
        6. If any attachments were not found:
            - Set the result value based on whether any attachments were saved.
            - Append the 'attachment not found' message to the output message.

        Args:
            email (MicrosoftGraphEmail): The email object to save the result.
        """
        email.cleanup_not_required_keys()
        self.json_results = email.to_json()
        if not self.params.save_only_attachment:
            self.output_message = self._email_success_msg
            return

        if not email.has_attachments:
            self.result_value = False
            self.output_message = self._no_attachment_msg

        if self.attachments_saved:
            self.output_message = self._attachment_success_msg

        if self.attachments_not_found:
            self.result_value = any(self.attachments_saved)
            self.output_message += self._attachment_not_found_msg

    @property
    def _email_success_msg(self) -> str:
        return "Email successfully saved!"

    @property
    def _attachment_success_msg(self) -> str:
        return (
            "Successfully saved the following attachments\n"
            f"{convert_list_to_comma_string(self.attachments_saved)}\n\n"
        )

    @property
    def _no_attachment_msg(self) -> str:
        return "No attachments available to save."

    @property
    def _attachment_not_found_msg(self) -> str:
        return (
            "The action didn't find the following attachments in the email with the "
            f'mail ID "{self.params.email_id}":\n '
            f"{convert_list_to_comma_string(self.attachments_not_found)}"
        )


def main() -> NoReturn:
    action = SaveEmailToCase()
    action.run()


if __name__ == "__main__":
    main()

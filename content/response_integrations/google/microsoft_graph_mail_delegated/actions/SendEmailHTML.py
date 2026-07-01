from __future__ import annotations

from typing import NoReturn

from collections.abc import MutableSequence

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from TIPCommon.types import SingleJson
from core import action_init
from core import constants
from core.datamodels import MicrosoftGraphEmail, MicrosoftGraphFolder
from core import exceptions
from core import utils
from core import MicrosoftGraphMailDelegatedManager as api_manager


class SendEmailHTML(Action[api_manager.ApiManager]):

    def __init__(self) -> None:
        super().__init__(constants.SEND_EMAIL_HTML_NAME)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{constants.SEND_EMAIL_HTML_NAME}".'
        )
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.send_from = extract_action_param(
            self.soar_action,
            param_name="Send From",
            default_value=constants.DEFAULT_MAILBOX,
            is_mandatory=True,
            print_value=True,
        )
        self.params.subject = extract_action_param(
            self.soar_action,
            param_name="Subject",
            is_mandatory=True,
            print_value=True,
        )
        self.params.send_to = extract_action_param(
            self.soar_action,
            param_name="Send to",
            is_mandatory=True,
            print_value=True,
        )
        self.params.send_to = string_to_multi_value(
            self.params.send_to,
            only_unique=True,
        )
        self.params.cc = extract_action_param(
            self.soar_action,
            param_name="CC",
            print_value=True,
        )
        self.params.cc = string_to_multi_value(self.params.cc, only_unique=True)
        self.params.bcc = extract_action_param(
            self.soar_action,
            param_name="BCC",
            print_value=True,
        )
        self.params.bcc = string_to_multi_value(self.params.bcc, only_unique=True)
        self.params.attachments_paths = extract_action_param(
            self.soar_action,
            param_name="Attachments Paths",
            print_value=True,
        )
        self.params.attachments_paths = string_to_multi_value(
            self.params.attachments_paths,
            only_unique=True,
        )
        self.params.email_html_template = extract_action_param(
            self.soar_action,
            param_name="Email HTML Template",
            default_value=constants.DEFAULT_EMAIL_HTML_TEMPLATE,
            is_mandatory=True,
            print_value=True,
        )
        self.params.reply_to = extract_action_param(
            self.soar_action,
            param_name="Reply-To Recipients",
            print_value=True,
        )
        self.params.attachment_location = extract_action_param(
            self.soar_action,
            param_name="Attachment Location",
            default_value="GCP Bucket",
            is_mandatory=True,
            print_value=True,
        )
        self.params.reply_to = string_to_multi_value(
            self.params.reply_to,
            only_unique=True,
        )

    def _validate_params(self) -> None:
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
                "The action failed to run because specified attachments were not "
                f"found: {invalid_paths}"
            )
            raise exceptions.InvalidAttachmentPathException(error_message)

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self._set_mailbox()
        send_email = self._send_email()
        sent_folder = self._get_sent_folder()
        sent_email = self._get_sent_draft_email(
            folder=sent_folder,
            email=send_email,
            timeout_in_ms=self.soar_action.execution_deadline_unix_time_ms,
        )
        self._set_action_result(sent_email)

    def _set_mailbox(self) -> None:
        self.params.send_from = utils.validate_mailbox(
            manager=self.api_client,
            mailbox=self.params.send_from,
            default_mailbox=self.api_client.mail_address,
        )

    def _send_email(self) -> MicrosoftGraphEmail:
        send_mail = self.api_client.send_vote_html_email(
            send_from=self.params.send_from,
            subject=self.params.subject,
            send_to=self.params.send_to,
            mail_content=self.params.email_html_template,
            cc=self.params.cc,
            bcc=self.params.bcc,
            attachments_data=self._get_attachment_data(),
            reply_to=self.params.reply_to,
        )

        return send_mail

    def _get_attachment_data(self) -> MutableSequence[SingleJson]:
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
        self.output_message = "The email was sent successfully."

    def _get_sent_draft_email(
        self,
        folder: MicrosoftGraphFolder,
        email: MicrosoftGraphEmail,
        timeout_in_ms: int,
    ) -> MicrosoftGraphEmail:
        return utils.get_sent_draft_email(
            manager=self.api_client,
            folder=folder,
            email=email,
            timeout_in_ms=timeout_in_ms,
        )


def main() -> NoReturn:
    SendEmailHTML().run()


if __name__ == "__main__":
    main()

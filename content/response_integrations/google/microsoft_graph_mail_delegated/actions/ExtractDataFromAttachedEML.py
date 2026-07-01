from __future__ import annotations

from typing import NoReturn

from collections.abc import Callable, Iterable, Mapping, MutableMapping

import email as email_lib
from email import message_from_string

import extract_msg

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string, string_to_multi_value
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from core import action_init
from core import constants
from core import datamodels
from core import EmailUtils
from core import exceptions
from core import utils
from core import MicrosoftGraphMailDelegatedManager as api_manager


class ExtractEmlData(Action[api_manager.ApiManager]):

    def __init__(self) -> None:
        super().__init__(constants.EXTRACT_EML_DATA_SCRIPT_NAME)
        self.email_utils = EmailUtils.EmailUtils(self.logger)
        self.output_message = ""
        self.invalid_ids = []
        self.email_with_no_attachments = []
        self.email_with_no_eml_attachments = []
        self.error_output_message = (
            f'Error executing action "{constants.EXTRACT_EML_DATA_SCRIPT_NAME}".'
        )
        self.result_value = True
        self.json_results = {}

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _extract_action_parameters(self) -> None:
        self.params.smime_auth = utils.get_integration_parameters(
            self.soar_action
        ).smime_auth
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
            is_mandatory=True,
            print_value=True,
            default_value=constants.DEFAULT_FOLDER_NAME,
        )
        self.params.mail_ids = extract_action_param(
            self.soar_action,
            param_name="Mail IDs",
            is_mandatory=False,
            print_value=True,
        )
        self.params.mail_ids = string_to_multi_value(
            self.params.mail_ids,
            only_unique=True,
        )
        self.params.regex_map_json = extract_action_param(
            self.soar_action,
            param_name="Regex Map JSON",
            default_value={},
            is_mandatory=False,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        if not is_empty_string_or_none(self.params.regex_map_json):
            self.params.regex_map_json = validator.validate_json(
                param_name="Regex Map JSON",
                json_string=self.params.regex_map_json,
                print_value=False,
            )

    def _perform_action(self, _) -> None:
        valid_mailboxes, invalid_mailboxes = utils.filter_valid_invalid_mailboxes(
            manager=self.api_client,
            mailboxes=self.params.mailboxes,
            default_mailbox=self.api_client.mail_address,
        )
        mailboxes = utils.get_mailboxes_result(
            manager=self.api_client,
            mailboxes=valid_mailboxes,
            folder_name=self.params.folder_name,
        )
        self._validate_mailbox_result(mailboxes, invalid_mailboxes)
        emails = self._get_emails_to_download_attachments(
            mailboxes=mailboxes.valid_mailboxes
        )
        emails = utils.get_emails_with_updated_metadata(
            manager=self.api_client,
            emails=emails,
            smime_auth=self.params.smime_auth,
        )
        attachments = self._get_attachments(email_attachments_to_download=emails)
        attachment_data = self._get_attachments_data(
            attachments,
            self.params.regex_map_json,
        )
        self._set_action_result(attachment_data, emails)

    def _validate_email_ids(
        self,
        emails: Iterable[datamodels.MicrosoftGraphEmail],
        mail_ids: Iterable[str],
    ) -> None:
        valid_ids = {email.id for email in emails} | {
            email.internet_message_id for email in emails
        }
        self.invalid_ids = set(mail_ids) - valid_ids

        if len(self.invalid_ids) == len(mail_ids):
            raise exceptions.EmailNotFoundException(
                "Failed to find any emails using the provided criteria!"
            )
        if self.invalid_ids:
            self.output_message += (
                "\n\nThe provided email IDs were not found: "
                f"{', '.join(self.invalid_ids)}"
            )
        if self.email_with_no_attachments:
            if len(self.invalid_ids) + len(self.email_with_no_attachments) == len(
                self.params.mail_ids
            ):
                self.result_value = False

    def _validate_emails_have_attachments(self) -> None:
        if self.email_with_no_attachments:
            self.output_message += (
                f"\nThe following email IDs do not have attachments: "
                f"{', '.join(self.email_with_no_attachments)}"
            )
        if self.email_with_no_eml_attachments:
            self.output_message += (
                "\n\nThe following email IDs do not have EML/ICS/MSG attachments: "
                f"{', '.join(self.email_with_no_eml_attachments)}\n\n"
            )
        if len(self.email_with_no_attachments) == len(self.params.mail_ids):
            raise exceptions.EmailWithoutAttachmentException(
                "The following email IDs do not have attachments: "
                f"{', '.join(self.params.mail_ids)}"
            )
        if len(self.email_with_no_eml_attachments) == len(self.params.mail_ids):
            raise exceptions.EmailWithoutAttachmentException(
                "The following email IDs do not have EML/ICS/MSG attachments: "
                f"{', '.join(self.params.mail_ids)}."
            )

    def _validate_mailbox_result(
        self,
        mailbox_result: utils.MailboxResult,
        invalid_mailboxes: list[str],
    ) -> None:
        if invalid_mailboxes and not mailbox_result.valid_mailboxes:
            raise exceptions.MailboxNotFoundException(
                "Failed to find any of the provided mailboxes:\n "
                f'"{convert_list_to_comma_string(invalid_mailboxes)}"'
            )

        if invalid_mailboxes and mailbox_result.valid_mailboxes:
            self.output_message += (
                "\n\nThe provided mailbox "
                f'"{convert_list_to_comma_string(invalid_mailboxes)}" '
                "was not found.\n"
            )

        if mailbox_result.invalid_folder_mailboxes:
            mailboxes_str = ", ".join(mailbox_result.invalid_folder_mailboxes)
            raise exceptions.FolderNotFoundException(
                "The action failed to run because the provided mailbox folder name "
                f'"{self.params.folder_name}" was not found in the mailbox/es '
                f"{mailboxes_str}"
            )

    def _set_action_result(
        self,
        attachment_data: datamodels.MicrosoftGraphEmail,
        emails: list[datamodels.MicrosoftGraphEmail],
    ) -> None:
        success_message: str = ""
        if attachment_data:
            attachment_names = [item["name"] for item in attachment_data]
            self.json_results = attachment_data
            success_message = (
                f'Extracted data from "{len(attachment_data)}" attached '
                "email files. \n\nFiles:\n"
                f'"{convert_list_to_comma_string(attachment_names)}"'
            )

        self._validate_emails_have_attachments()
        self._validate_email_ids(emails, self.params.mail_ids)
        self.output_message = success_message + self.output_message
        if self.invalid_ids or self.email_with_no_attachments:
            self.result_value = False

    def _get_emails_to_download_attachments(
        self,
        mailboxes: list[datamodels.MicrosoftGraphFolder],
    ) -> list[datamodels.MicrosoftGraphEmail]:
        return utils.get_emails_with_email_ids(
            manager=self.api_client,
            mailboxes=mailboxes,
            email_ids=self.params.mail_ids,
        )

    def _get_attachments(
        self,
        email_attachments_to_download: Iterable[datamodels.MicrosoftGraphEmail],
    ) -> list[datamodels.MicrosoftGraphAttachment]:
        """
        Downloads and returns a list of email attachment objects from
        the Microsoft Graph API.
        Args:
            email_attachments_to_download (Iterable[MicrosoftGraphEmail]): A list of
            MicrosoftGraphEmail objects of emails with attachments to be downloaded.

        Returns:
            list[MicrosoftGraphAttachment]: A list of MicrosoftGraphAttachment objects
            containing downloaded attachments.
        """
        attachments = []
        for email in email_attachments_to_download:
            if not email.has_attachments:
                self.email_with_no_attachments.append(email.id)
                continue

            email_attachments = utils.get_attachments(
                manager=self.api_client,
                email=email,
            )
            attachments.extend(self._filter_eml_ics_msg_attachments(email_attachments))

        return attachments

    def _filter_eml_ics_msg_attachments(
        self,
        attachments: list[datamodels.MicrosoftGraphAttachment],
    ) -> list[datamodels.MicrosoftGraphAttachment]:
        return [
            attachment
            for attachment in attachments
            if attachment.is_eml or attachment.is_ics or attachment.is_msg
        ]

    def _get_attachments_data(
        self,
        attachments: Iterable[datamodels.MicrosoftGraphAttachment],
        regex_map: Mapping[str, str],
    ) -> list[SingleJson]:
        """Fetch EML data from message attachments.

        Args:
            attachments(list[MicrosoftGraphAttachment]): List of
            MicrosoftGraphAttachment objects
            regex_map(dict[str, str]): Dictionary representing the regex map

        Returns:
            list[SingleJson]: List of dictionaries with message EML attachments data.
        """
        eml_data: list[SingleJson] = []
        for attachment in attachments:
            if not (attachment.is_eml or attachment.is_msg or attachment.is_ics):
                continue

            if attachment.is_smime:
                attachment_content = attachment.content_bytes

            else:
                attachment_content = self.api_client.load_attachment_content(
                    folder_id=attachment.folder_id,
                    email_id=attachment.email_id,
                    attachment_id=attachment.id,
                    mail_address=attachment.mailbox_name,
                )
            attachment_name = attachment.name or constants.EMPTY_EMAIL_SUBJECT
            data: SingleJson = {}
            if attachment.is_eml:
                data = self._get_attachment_data(
                    attachment_content=attachment_content,
                    msg_id=attachment.id,
                    attachment_name=attachment_name,
                    regex_map=regex_map,
                    extract_func=self._extract_eml_data,
                )

            if attachment.is_ics:
                data = self._get_attachment_data(
                    attachment_content=attachment_content,
                    msg_id=attachment.id,
                    attachment_name=attachment_name,
                    regex_map=regex_map,
                    extract_func=self._extract_ics_data,
                )

            if attachment.is_msg:
                data = self._get_attachment_data(
                    attachment_content=attachment_content,
                    msg_id=attachment.id,
                    attachment_name=attachment_name,
                    regex_map=regex_map,
                    extract_func=self._extract_msg_data,
                )
            if not data:
                continue

            eml_data.append(data)

        return eml_data

    def _get_attachment_data(
        self,
        attachment_content: bytes,
        msg_id: str,
        attachment_name: str,
        regex_map: Mapping[str, str],
        extract_func: Callable[[bytes], MutableMapping[str, str]],
    ) -> SingleJson | None:
        data = extract_func(attachment_content)
        if not data:
            return None

        email_html = data.get("html", "")
        email_text = data.get("text", "")
        if email_html:
            data["regex"] = self.email_utils.extract_regex_from_content(
                content=email_html, regex_map=regex_map
            )
        if email_text:
            data["regex_from_text_part"] = self.email_utils.extract_regex_from_content(
                content=email_text, regex_map=regex_map
            )
        data["id"] = msg_id
        data["name"] = attachment_name

        return data

    def _extract_eml_data(self, attachment_content: bytes) -> MutableMapping[str, str]:
        decrypted_mime_content = EmailUtils.get_decrypted_mime_content(
            mime_content=attachment_content,
            smime_auth=self.params.smime_auth,
            logger=self.logger,
        )
        msg = message_from_string(EmailUtils.get_unicode_str(decrypted_mime_content))
        return self._extract_common_data(msg, "EML")

    def _extract_msg_data(self, attachment_content: bytes) -> MutableMapping[str, str]:
        msg = extract_msg.Message(attachment_content)
        return self._extract_common_data(msg, "MSG")

    def _extract_ics_data(self, attachment_content: bytes) -> SingleJson | None:
        data = self.email_utils.convert_siemplify_ics_to_connector_msg(
            attachment_content
        )
        if data:
            return self.extract_ics_data(calendar_data=data[0])

        return None

    def _extract_common_data(
        self,
        msg: email_lib.message.Message | extract_msg.Message,
        msg_type: str,
    ) -> MutableMapping[str, str]:
        subject = self._extract_subject(msg)
        sender, to, date = self._extract_metadata(msg)
        text_body, html_body = self._extract_content(msg)

        return {
            "type": msg_type,
            "subject": subject,
            "from": sender,
            "to": to,
            "date": date,
            "text": text_body,
            "html": html_body,
        }

    def _extract_metadata(
        self,
        msg: email_lib.message.Message | extract_msg.Message,
    ) -> tuple[str, str, str]:
        """Extract metadata (sender, recipient, date) from EML

        Args:
            msg (email.message.Message | extract_msg.Message): An eml or msg object

        Returns:
            tuple: sender, recipient, date
        """
        if isinstance(msg, extract_msg.Message):
            EmailUtils.EmailUtils.replaced_msg_header_unsupported_encoding(msg, "from")
            EmailUtils.EmailUtils.replaced_msg_header_unsupported_encoding(msg, "to")
            date = EmailUtils.EmailUtils.extract_unixtime_date_from_msg(msg.date)

            return (msg.sender.strip(), msg.to.strip(), date)

        return (
            msg.get("from", "").strip(),
            msg.get("to", "").strip(),
            msg.get("date", "").strip(),
        )

    def _extract_subject(
        self,
        msg: email_lib.message.Message | extract_msg.Message,
    ) -> str:
        """Extract message subject from email message.
        Args:
            msg (email_lib.message.Message | extract_msg.Message): EML or MSG object.

        Returns:
            str: Subject text.
        """
        raw_subject = (
            msg.subject if isinstance(msg, extract_msg.Message) else msg.get("subject")
        )
        if not raw_subject:
            return ""

        try:
            parsed_value, encoding = email_lib.header.decode_header(raw_subject)[0]
            if encoding is None:
                return parsed_value

            return parsed_value.decode(encoding)

        except UnicodeDecodeError as e:
            self.logger.warn(f"Unable to decode email subject: {e}")
            return "Unable to decode email subject"

    def _extract_content(
        self,
        msg: email_lib.message.Message | extract_msg.Message,
    ) -> tuple[str, str]:
        """Extracts content from an e-mail message.

        Args:
            msg (email_lib.message.Message | extract_msg.Message): EML or MSG object.

        Returns:
            tuple: plain text, html text
        """
        if isinstance(msg, extract_msg.Message):
            return msg.body, msg.htmlBody

        def extract_parts(content_type: str) -> str:
            parts = list(
                email_lib.iterators.typed_subpart_iterator(msg, "text", content_type)
            )
            body_parts = []
            parent_charset = EmailUtils.get_charset(msg)
            for part in parts:
                charset = EmailUtils.get_charset(part, parent_charset)
                try:
                    body_parts.append(
                        self.email_utils.decode_by_charset(
                            part.get_payload(decode=True),
                            charset,
                            constants.DEFAULT_CHARSET,
                        )
                    )
                except (UnicodeDecodeError, UnicodeEncodeError) as e:
                    self.logger.warn(f"Failed to decode payload: {e}")

            return "\n".join(body_parts).strip()

        if not msg.is_multipart():
            body = self.email_utils.decode_by_charset(
                msg.get_payload(decode=True),
                EmailUtils.get_charset(msg),
                constants.DEFAULT_CHARSET,
            )
            return body.strip(), body.strip()

        return extract_parts("plain"), extract_parts("html")

    def extract_ics_data(self, calendar_data: SingleJson) -> MutableMapping[str, str]:
        """Extracts data from an ICS calendar entry.

        Args:
            calendar_data (SingleJson): Calendar JSON data.

        Returns:
            dict[str, str]: calender soar json data.
        """
        content_type = calendar_data["body"]["contentType"]
        is_text_content = content_type in constants.TEXT_CONTENT_TYPE
        content = calendar_data["body"]["content"]

        return {
            "type": "ICS",
            "subject": calendar_data["subject"],
            "from": calendar_data["from"]["emailAddress"]["address"],
            "to": ",".join(
                [
                    data["emailAddress"]["address"]
                    for data in calendar_data["toRecipients"]
                ]
            ),
            "date": calendar_data["receivedDateTime"],
            "text": content if is_text_content else "",
            "html": content if not is_text_content else "",
        }


def main() -> NoReturn:
    ExtractEmlData().run()


if __name__ == "__main__":
    main()

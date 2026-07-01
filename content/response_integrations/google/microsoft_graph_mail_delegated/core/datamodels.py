from __future__ import annotations

from base64 import b64encode
import copy
import dataclasses
import hashlib

from datetime import datetime
from TIPCommon.base.interfaces import ScriptLogger
import TIPCommon.transformation
from TIPCommon.types import SingleJson
from . import constants


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    azure_ad_endpoint: str
    microsoft_graph_endpoint: str
    client_id: str
    secret_id: str
    tenant: str
    user_mailbox: str
    refresh_token: str
    redirect_url: str
    mail_field_source: bool
    verify_ssl: bool
    smime_auth: SmimeAuth
    siemplify_logger: ScriptLogger


@dataclasses.dataclass(slots=True)
class SmimeAuth:
    private_key_b64: str = None
    certificate_b64: str = None
    ca_certificate_b64: str = None


class BaseModel:
    """Base model for inheritance"""

    def __init__(self, raw_data: SingleJson):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return TIPCommon.transformation.dict_to_flat(self.to_json())

    def cleanup_not_required_keys(self):
        self.raw_data.pop(constants.ETAG_VALUE, None)
        self.raw_data.pop(constants.CONTEXT_VALUE, None)


class MicrosoftGraphFileAttachment(BaseModel):
    """Class for MicrosoftGraphFileAttachment object."""

    def __init__(
        self,
        raw_data: SingleJson,
        attachment_id: str | None = None,
        size: int | None = None,
        contentType: str | None = None,
        name: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(raw_data)
        self.id = attachment_id
        self.size = size
        self.name = name
        self.content_type = contentType
        self.odata_type = kwargs["@odata.type"]
        self.__content = None

    def as_json(self) -> SingleJson:
        """Get api response data for File Attachment as json.

        Returns:
            SingleJson: api response data for File Attachment as json.
        """
        return self.raw_data

    def md5_hash(self) -> str:
        """md5 hash for the content.

        Returns:
            str: md5 type string.
        """
        return hashlib.md5(self.content).hexdigest()

    def as_event(self) -> SingleJson:
        """Email response json as event.

        Returns:
            SingleJson: flat dictionary object for alert event.
        """
        event_data = copy.deepcopy(self.raw_data)
        return TIPCommon.transformation.dict_to_flat(event_data)

    @property
    def content(self) -> bytes | None:
        return self.__content

    @content.setter
    def content(self, value: bytes) -> bytes:
        self.__content = value

    @property
    def is_eml(self) -> bool:
        """Check if the email attachment is an eml type.

        Returns:
            bool: email attachment is an eml type otherwise bool.
        """
        if self.is_file_attachment:
            return ".eml" in self.name

        if self.is_item_attachment and not self.content_type:
            return True

        return self.content_type == "message/rfc822"

    @property
    def is_ics(self) -> bool:
        """Check if the email attachment is an ics type.

        Returns:
            bool: email attachment is an ics type otherwise bool.
        """
        if self.is_file_attachment:
            return ".ics" in self.name
        return self.content_type in ("application/ics", "text/calendar")

    @property
    def is_msg(self) -> bool:
        """Check if the email attachment is a msg type.

        Returns:
            bool: email attachment is a msg type otherwise bool.
        """
        if self.is_file_attachment:
            return ".msg" in self.name
        return self.content_type == "application/vnd.ms-outlook"

    @property
    def is_file_attachment(self) -> bool:
        """Check if email attachment is a file type attachment.

        Returns:
            bool: True if attachment is file type otherwise False.
        """
        return self.odata_type == "#microsoft.graph.fileAttachment"

    @property
    def is_item_attachment(self) -> bool:
        """Check if email attachment is an item type attachment.

        Returns:
            bool: True if attachment is item type otherwise False.
        """
        return self.odata_type == "#microsoft.graph.itemAttachment"

    @property
    def is_to_large(self) -> bool:
        """Check if attachment size is too large.

        Returns:
            bool: True if size of the attachment is too large than default size,
            False otherwise.
        """
        return self.size > constants.MAX_FILE_SIZE


class MicrosoftGraphEmail(BaseModel):
    """Class for Email api response.

    Args:
        BaseModel: BaseModel class.
    """

    def __init__(
        self,
        raw_data: SingleJson,
        mailbox_name: str | None = None,
        folder_name: str | None = None,
        mail_id: str | None = None,
        internetMessageId: str | None = None,
        receivedDateTime: str | None = None,
        body: str | None = None,
        subject: str | None = None,
        hasAttachments: bool = False,
        internetMessageHeaders: str | None = None,
        parentFolderId: str | None = None,
        content: str | None = None,
        mime_content: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(raw_data)
        self.internet_message_id = internetMessageId
        self.id = mail_id
        self.received_date_time = receivedDateTime
        self.body = body or {}
        self.subject = subject
        self.has_attachments = hasAttachments
        self.internet_message_headers = internetMessageHeaders or []
        self.folder_id = parentFolderId
        self.mailbox_name = mailbox_name
        self.folder_name = folder_name
        self.ics_attachments = []
        self.eml_attachments = []
        self.msg_attachments = []
        self.file_attachments = []
        self.conversation_id = kwargs.get("conversationId")
        self.sender = kwargs.get("sender", {}).get("emailAddress", {}).get("address")
        self.all_recipients = (
            kwargs.get("toRecipients", [])
            + kwargs.get("ccRecipients", [])
            + kwargs.get("bccRecipients", [])
        )
        self.content = content
        self._mime_content = mime_content
        self._parse_eml = None
        self.attachments = kwargs.get("attachments", [])

    @property
    def recipients(self) -> list[str]:
        """Get list of all recipients in a mail.
        e.g.: ['toRecipients', 'ccRecipients', 'bccRecipients']

        Returns:
            list[str]: list of all recipients.
        """
        return list(
            {
                recipient.get("emailAddress", {}).get("address", "")
                for recipient in self.all_recipients
            }
        )

    @property
    def body_content(self) -> str:
        """Get content from email body.

        Returns:
            str: content from email body.
        """
        return self.body.get("content")

    @property
    def mime_content(self) -> bytes:
        """Get mime content of email"""
        return self._mime_content

    @mime_content.setter
    def mime_content(self, value: bytes) -> None:
        self._mime_content = value

    @property
    def parsed_email(self) -> SingleJson:
        return self._parse_eml

    @parsed_email.setter
    def parsed_email(self, value: SingleJson) -> None:
        self._parse_eml = value

    @property
    def parsed_time(self) -> datetime:
        """Get parsed datetime object.

        Returns:
            datetime: parsed datetime object.
        """
        return datetime.strptime(self.received_date_time, constants.TIME_FORMAT)

    @property
    def timestamp(self) -> datetime:
        """Get parsed timestamp.

        Returns:
            datetime: parsed timestamp.
        """
        return self.parsed_time.timestamp()

    def set_attachments(self, attachments: list[MicrosoftGraphFileAttachment]) -> None:
        """add attachments to the different type attachment's list.

        Args:
            attachments (List[MicrosoftGraphFileAttachment]): list of
            attachments.
        """
        for att in attachments:
            if att.is_ics:
                self.ics_attachments.append(att)
            elif att.is_eml:
                self.eml_attachments.append(att)
            elif att.is_msg:
                self.msg_attachments.append(att)
            elif att.is_file_attachment and att.content is not None:
                self.file_attachments.append(att)

    @property
    def is_smime_email(self) -> bool:
        """Check if email has smime attachment.

        Returns:
            bool: True if email has smime attachment otherwise False.
        """
        if (
            self.attachments
            and self.attachments[0]["contentType"]
            in constants.SMIME_ATTACHMENT_CONTENT_TYPES
        ):
            return True

        return False

    def set_smime_email_body(self) -> None:
        """Sets the email body content for S/MIME emails.

        If the email is parsed and contains S/MIME content, this method updates
        the raw_data dictionary with the parsed body content. It prioritizes
        the plaintext body if the original body content is of a text type,
        otherwise it uses the parsed body.
        """
        if not self.parsed_email:
            return

        self.raw_data["bodyPreview"] = self.parsed_email["body"]
        self._set_smime_body_content()
        self._set_smime_unique_body_content()

    def _set_smime_body_content(self) -> None:
        self.raw_data["body"]["content"] = (
            self.parsed_email["plaintext_body"]
            if self.raw_data["body"]["contentType"] in constants.TEXT_CONTENT_TYPE
            else self.parsed_email["html_body"]
        )

    def _set_smime_unique_body_content(self) -> None:
        unique_body = self.raw_data.get("uniqueBody", {})
        if unique_body:
            self.raw_data["uniqueBody"]["content"] = (
                self.parsed_email["plaintext_body"]
                if self.raw_data["uniqueBody"]["contentType"]
                in constants.TEXT_CONTENT_TYPE
                else self.parsed_email["html_body"]
            )

    def as_json(self) -> SingleJson:
        """Get email data as json dict.

        Returns:
            SingleJson: api response data for Email as json.
        """
        return self.raw_data

    def as_alert(self):
        pass

    def create_event(
        self,
        additional_info: SingleJson | None = None,
        attachment_data: SingleJson | None = None,
        headers_to_add_to_events: list[str] | tuple = tuple(),
    ) -> SingleJson:
        """Create an event from an eml content.

        Args:
            additional_info (SingleJson | None): Additional event info
            (parsed urls, e.t.c)
            attachment_data (SingleJson | None): Passed if event is created
            for attachment
            headers_to_add_to_events (list[str] | tuple): which headers to
            include in the event data

        Returns:
            SingleJson: event dict.
        """
        event_data = copy.deepcopy(
            self.raw_data if attachment_data is None else attachment_data
        )
        for field in constants.EMAIL_LIST_FIELDS:
            if field in event_data:
                for index, email_dict in enumerate(event_data[field]):
                    iterable_unpacked = email_dict.get("emailAddress", {}).items()
                    for field_name, field_value in iterable_unpacked:
                        event_data[f"{field}_emailAddress_{field_name}_{index + 1}"] = (
                            field_value
                        )
                del event_data[field]

        if headers_to_add_to_events:
            filtered_headers = (
                [
                    header_dict
                    for header_dict in self.internet_message_headers
                    if header_dict["name"] in headers_to_add_to_events
                ]
                if headers_to_add_to_events[0] != "None"
                else []
            )
            event_data["internetMessageHeaders"] = filtered_headers

        existing_headers = event_data.get("internetMessageHeaders", [])
        if existing_headers:
            headers_formatted = {}
            for header in existing_headers:
                headers_formatted[header["name"]] = headers_formatted.get(
                    header["name"], []
                ) + [header["value"]]
            event_data["internetMessageHeaders"] = headers_formatted

        event_data.update(additional_info or {})
        flat_event_data = TIPCommon.transformation.dict_to_flat(event_data)

        flat_event_data["device_product"] = constants.DEVICE_PRODUCT
        flat_event_data["device_vendor"] = constants.VENDOR
        flat_event_data["event_name"] = constants.ORIGINAL_EMAIL_EVENT_NAME
        flat_event_data["monitored_mailbox_name"] = self.mailbox_name
        flat_event_data["email_folder"] = self.folder_name

        if attachment_data:
            flat_event_data["event_name"] = constants.ATTACHED_EMAIL_EVENT_NAME
            flat_event_data["original_email_id"] = self.id

        return self._set_event_body(event_data, flat_event_data)

    def _set_event_body(
        self,
        event_data: SingleJson,
        flat_event_data: SingleJson,
    ) -> SingleJson:
        body_preview = event_data.get("bodyPreview", "")
        if not body_preview:
            flat_event_data["bodyPreview"] = self.parsed_email["uniqueBody"]["content"]

        unique_body = event_data.get("uniqueBody", {})
        unique_body_content = unique_body.get("content", "")
        unique_body_content_type = unique_body.get("contentType", "")
        if unique_body_content in ["", constants.EMPTY_HTML_CONTENT_BODY]:
            if unique_body_content_type in constants.TEXT_CONTENT_TYPE:
                flat_event_data["uniqueBody_content"] = self.parsed_email["uniqueBody"][
                    "content"
                ]
            else:
                flat_event_data["uniqueBody_content"] = self.parsed_email["body"][
                    "content"
                ]

        body = event_data.get("body", {})
        body_content = body.get("content", "")
        body_content_type = body.get("contentType", "")
        if body_content in ["", constants.EMPTY_HTML_CONTENT_BODY]:
            if body_content_type in constants.TEXT_CONTENT_TYPE:
                flat_event_data["body_content"] = self.parsed_email["uniqueBody"][
                    "content"
                ]
            else:
                flat_event_data["body_content"] = self.parsed_email["body"]["content"]

        return flat_event_data

    def to_table(self) -> dict[str, str]:
        """Returns dict object to create case wall table.

        Returns:
            dict[str, str]: dict object for table.
        """
        return {
            "Mail ID": self.id,
            "Received Date": self.received_date_time,
            "Sender": self.sender,
            "Recipients": ", ".join(self.recipients),
            "Subject": self.subject,
        }

    def to_compact_json(self) -> SingleJson:
        """Returns a compact JSON representation of the email.

        Returns:
            SingleJson: A compact JSON representation of the email.
        """
        return {
            "id": self.id,
            "internetMessageId": self.internet_message_id,
            "sender": self.sender,
            "subject": self.subject,
            "toRecipients": ", ".join(self.recipients),
            "receivedDateTime": self.received_date_time,
        }


class MicrosoftGraphFolder(BaseModel):
    """Create MicrosoftGraphFolder folder object."""

    def __init__(
        self,
        raw_data: str,
        folder_id: str,
        display_name: str,
        mailbox_name: str | None = None,
    ) -> None:
        super().__init__(raw_data=raw_data)
        self.id = folder_id
        self.display_name = display_name
        self.mailbox_name = mailbox_name


class MicrosoftGraphAttachment(MicrosoftGraphFileAttachment):
    """Create MicrosoftGraphAttachment attachment object."""

    def __init__(
        self,
        raw_data: dict,
        mailbox_name: str | None = None,
        folder_name: str | None = None,
        email_id: str | None = None,
        folder_id: str | None = None,
        attachment_id: str | None = None,
        name: str | None = None,
        size: str | None = None,
        content_bytes: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(raw_data, **kwargs)
        self.mailbox_name = mailbox_name
        self.folder_name = folder_name
        self.folder_id = folder_id
        self.email_id = email_id
        self.id = attachment_id
        self.name = name
        self.size = size
        self.content_bytes = content_bytes
        self.is_smime = kwargs.get("isSmime", False)
        self.file_ext = kwargs.get("fileExt")

    @classmethod
    def from_json(
        cls,
        attachment_json: SingleJson,
        mailbox_name: str,
        folder_name: str,
        folder_id: str,
        email_id: str,
    ) -> MicrosoftGraphAttachment:
        """Create a MicrosoftGraphAttachment instance from JSON data.

        Args:
            attachment_json (SingleJson): JSON data representing the attachment.
            mailbox_name (str): The name of the mailbox.
            folder_name (str): The name of the folder.
            folder_id (str): The ID of the folder.
            email_id (str): The ID of the email.

        Returns:
            MicrosoftGraphAttachment: An instance of MicrosoftGraphAttachment.
        """
        return cls(
            raw_data=attachment_json,
            mailbox_name=mailbox_name,
            folder_name=folder_name,
            email_id=email_id,
            folder_id=folder_id,
            attachment_id=attachment_json.get("id"),
            content_bytes=attachment_json.get("contentBytes", ""),
            **attachment_json,
        )

    @property
    def content_bytes_as_b64_string(self) -> str:
        return b64encode(self.content_bytes).decode()


class UserOOFSettings(BaseModel):
    """Model for UserOOFSettings api response."""

    def __init__(self, raw_data: str) -> None:
        super().__init__(raw_data=raw_data)
        self.id = raw_data.get("id")
        self.availability = raw_data.get("availability")
        self.activity = raw_data.get("activity")
        self.status_message = raw_data.get("statusMessage")
        self.ooo_settings = raw_data.get("outOfOfficeSettings")
        self.ooo_message = self.ooo_settings.get("message")
        self.is_ooo = self.ooo_settings.get("isOutOfOffice")

    def to_table(self) -> dict[str, str]:
        """Returns dict object to create case wall table.

        Returns:
            dict[str, str]: dict object for table.
        """
        return {
            "Is Out of Office": self.is_ooo,
            "Out of Office message": self.ooo_message,
            "Status Message": self.status_message,
            "Availability": self.availability,
            "Activity": self.activity,
        }

    def get_enrichment_data(self) -> dict[str, str]:
        """Returns dict object to create case wall enrichment table.

        Returns:
            dict[str, str]: dict object for table.
        """
        return {
            "Is Out of Office": self.is_ooo,
            "Out of Office message": self.ooo_message,
        }

    def to_enrichment_data(self) -> dict[str, str]:
        """Function that prepares the user's data to be used in the table.

        Returns:
            dict[str, str]: Dict containing enrichment data.
        """
        clean_enrichment_data = {
            k: v for k, v in self.get_enrichment_data().items() if v
        }

        return TIPCommon.transformation.add_prefix_to_dict(
            clean_enrichment_data, constants.INTEGRATION_NAME
        )


@dataclasses.dataclass(frozen=True)
class SearchResultData(BaseModel):
    raw_data: SingleJson
    hit_id: str
    rank: int
    summary: str

    @classmethod
    def from_json(
        cls,
        response_json: SingleJson,
    ) -> SearchResultData:
        """Creates a `SearchResultData` object from a JSON response.

        This method constructs a `SearchResultData` object using data extracted
        from the given JSON response.

        Args:
            response_json (SingleJson): The JSON representation of a search hit,
                containing details such as hit ID, rank, and summary.

        Returns:
            SearchResultData: The constructed `SearchResultData` object.
        """
        return cls(
            raw_data=response_json,
            hit_id=response_json.get("hitId"),
            rank=response_json.get("rank"),
            summary=response_json.get("summary"),
        )

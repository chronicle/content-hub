from __future__ import annotations
from typing import Any

from collections.abc import Iterable, MutableMapping, MutableSequence

import email
import hashlib
import re
import time
import urllib.parse
from datetime import datetime
from base64 import b64decode, b64encode
from io import BytesIO
from unicodedata import bidirectional

import compressed_rtf
import extract_msg
from extract_msg.exceptions import ExMsgBaseException
from olefile.olefile import OleFileError
import html2text

from emaildata.metadata import MetaData
from emaildata.metadata import text_to_utf8
from icalendar import Calendar
from pyth.plugins.rtf15.reader import Rtf15Reader
from pyth.plugins.xhtml.writer import XHTMLWriter

from TIPCommon.base.interfaces import ScriptLogger
from TIPCommon.data_models import SmimeEmailConfig
from TIPCommon.encryption import decrypt_email
from TIPCommon.types import SingleJson
from . import constants
from .datamodels import MicrosoftGraphEmail, SmimeAuth


ANSWER_PLACEHOLDER_PATTERN = "(?<={{)[^{]*(?=}})"
CHARS_TO_STRIP = " \r\n"
DEFAULT_DIVIDER = ";"
DEFAULT_LIST_DELIMITER = ";"
EMAIL_PREFIX = "mailto:"
INNER_MSG_NOT_SUPPORTED = "Inner .msg attachment is present but not supported."
MAIL_SUBJECT_KEY = "subject"
MESSAGE_ID_FORMAT = "<{}>"
URL_ENCLOSING_PREFIX = "["
URL_ENCLOSING_SUFFIX = "]"
URLS_REGEX = (
    r"(?i)\[?(?:(?:(?:http|https)(?:://))|www\.(?!://))(?:[a-zA-Z0-9\-\._~:;"
    r"/\?#\[\]@!\$&'\(\)\*\+,=%])+"
)
URLS_REGEX_COMPLEX = (
    r"(?i)\[?(?:(?:(?:http|https)(?:://))|www\.(?!://))(?:[a-zA-Z0-9\-\._~:;"
    r"/\?#\[\]@!\$&'\(\)\*\+,=%<>])+"
)
SIEMPLIFY_MAIL_DICT_HTML_BODY_KEY = "html_body"
SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY = "plaintext_body"
SIEMPLIFY_MAIL_DICT_RESOLVED_BODY_KEY = "body"
SIEMPLIFY_MAIL_DICT_TO_KEY = "to"
SIEMPLIFY_MAIL_DICT_CC_KEY = "cc"
SIEMPLIFY_MAIL_DICT_BCC_KEY = "bcc"
SIEMPLIFY_MAIL_DICT_SENDER_KEY = "sender"
SIEMPLIFY_MAIL_DICT_SUBJECT_KEY = "subject"
SIEMPLIFY_MAIL_DICT_MESSAGE_ID_KEY = "message_id"
SIEMPLIFY_MAIL_DICT_RECEIVERS_KEY = "receivers"
SIEMPLIFY_MAIL_DICT_REPLY_TO_KEY = "reply_to"
SIEMPLIFY_MAIL_DICT_IN_REPLY_TO_KEY = "in_reply_to"
SIEMPLIFY_MAIL_DICT_RAW_EML_KEY = "raw"
SIEMPLIFY_MAIL_DICT_DATE_KEY = "date"
SIEMPLIFY_MAIL_DICT_TIMESTAMP_KEY = "timestamp"
SIEMPLIFY_MAIL_DICT_UNIXTIME_DATE_KEY = "unixtime_date"
SIEMPLIFY_MAIL_DICT_EMAIL_ID_KEY = "email_uid"
SIEMPLIFY_MAIL_DICT_ANSWER_ID_KEY = "answer"
SIEMPLIFY_MAIL_DICT_NAMES_KEY = "names"
SIEMPLIFY_MAIL_DICT_DISPLAY_NAME_KEY = "display_name"


# pylint: disable=broad-exception-caught


def decode_url(url: str) -> str:
    return urllib.parse.unquote_plus(url)


def filter_emails_with_regexes(
    emails: Iterable[MicrosoftGraphEmail],
    exclude_regex_pattern: str | None = None,
) -> tuple[MutableSequence[MicrosoftGraphEmail], MutableSequence[MicrosoftGraphEmail]]:
    """Walks through all provided emails, matches their subject and all possible body
    fields against regexes and takes just non matching ones.
    Args:
        emails(Iterable): Iterable email instances
        exclude_regex_pattern(str | None): String representing regex to exclude email by
        matching subject or body.

    Returns:
        tuple[
            MutableSequence[MicrosoftGraphEmail],
            MutableSequence[MicrosoftGraphEmail]
        ]: Tuple containing MutableSequence of filtered email.
    """
    filtered_emails: MutableSequence[MicrosoftGraphEmail] = []
    excluded: MutableSequence[MicrosoftGraphEmail] = []

    for mail in emails:
        if is_matching_exclude_patterns(mail, exclude_regex_pattern):
            excluded.append(mail)
        else:
            filtered_emails.append(mail)

    return filtered_emails, excluded


def is_matching_exclude_patterns(
    message: MicrosoftGraphEmail,
    exclude_regex_pattern: str,
) -> bool:
    """Get first message content from list which is not matching patterns.
    Args:
        message(MicrosoftGraphEmail): MicrosoftGraphEmail object.
        exclude_regex_pattern(str): Regex pattern, which would exclude emails with
        matching subject or body.

    Returns:
        bool: True if matches one of the exclude patterns; False - otherwise.
    """

    if exclude_regex_pattern:
        message_body = message.body.get("content")
        if message_body and re.findall(exclude_regex_pattern, message_body):
            return True
        if message.subject and re.findall(exclude_regex_pattern, message.subject):
            return True

    return False


def get_html_urls(html_content: str) -> tuple[str, str]:
    """Get urls from html content
    Args:
        html_content(str): The html content.

    Returns:
        tuple[str, str] Comma-separated list of visible urls, comma-separated list of
        not visible urls from original src attribute.
    """
    regex_object = re.compile(URLS_REGEX_COMPLEX)
    urls_list, original_src_urls_list = get_html_urls_from_html_2_text_obj(html_content)

    urls_list = list(
        {
            check_url_enclosing(decode_url(regex_object.search(url).group(0)))
            for url in urls_list
            if regex_object.search(url)
        }
    )
    original_src_urls_list = list(
        {
            check_url_enclosing(decode_url(regex_object.search(url).group(0)))
            for url in original_src_urls_list
            if regex_object.search(url)
        }
    )

    return DEFAULT_DIVIDER.join(urls_list), DEFAULT_DIVIDER.join(original_src_urls_list)


def check_url_enclosing(url: str) -> str:
    """Check if url enclosed and remove enclosing characters.
    Args:
        url(str): URL to check.

    Returns:
        str: Transformed url.
    """
    return (
        url[1:-1]
        if url.startswith(URL_ENCLOSING_PREFIX) and url.endswith(URL_ENCLOSING_SUFFIX)
        else url
    )


def get_html_urls_from_html_2_text_obj(
    html_content: str,
) -> tuple[MutableSequence[str], MutableSequence[str]]:
    """Create a HTML2Text object and get html urls.
    Args:
        html_content(str): The html content.

    Returns:
        tuple[MutableSequence[str], MutableSequence[str]]: The list of visible urls,
        the list of not visible urls from original src attribute.
    """
    html_renderer = html2text.HTML2Text()
    html_renderer.ignore_tables = True
    html_renderer.protect_links = True
    html_renderer.ignore_images = False
    html_renderer.ignore_links = False
    html_renderer.handle(html_content)
    return html_renderer.html_links, html_renderer.html_links_original_src


def get_charset(message: email.message.Message, default_charset: str = "utf-8") -> str:
    """Get the message charset
    Args:
        message(email.message.Message) An eml object.
        default_charset(str): Default charset, which should be used.

    Returns:
        str: Charset name.
    """
    try:
        charset = message.get_content_charset() or message.get_charset()
        if charset:
            if charset.find('"') > 0:
                charset = charset[: charset.find('"')]
            if charset == "iso-8859-8-i":
                charset = "iso-8859-8"
            return charset

    except Exception:
        pass

    return default_charset


def get_unicode_str(value: Any) -> str:
    """Checks type of the string and if it's a binary string, then decodes it to unicode
    Args:
        value(Any): string or binary string.

    Returns:
        str: Unicode decoded string.
    """
    try:
        return value.decode() if isinstance(value, bytes) else str(value)

    except Exception:
        return value


def decode_header_value(header_value: str) -> str:
    """Extract message header value from email message.
    Args:
        header_value(str): The raw header value.

    Returns:
        str: The parsed header value.
    """
    if not header_value:
        return ""

    try:
        parsed_value, encoding = email.header.decode_header(header_value)[0]
        if isinstance(parsed_value, str):
            return parsed_value

        if not encoding:
            return parsed_value.decode("utf-8")

        return parsed_value.decode(encoding)

    except Exception:
        try:
            return parsed_value.decode()

        except Exception:
            return "Unable to decode email subject"


def is_rtl(text: str) -> bool:
    """Checks if presented text is bidirectional:
    https://en.wikipedia.org/wiki/Right-to-left_mark. It's required for normal
    representation of such languages as Hebrew.

    Args:
        text(str): Input text to check

    Return:
        bool: True - if text is bidirectional; False - otherwise.
    """
    x = len([None for ch in text if bidirectional(ch) in ("R", "AL")]) / float(
        len(text)
    )
    if x > 0:
        return True

    return False


def add_rtl_html_divs_to_body(body: str) -> str:
    """Wraps entire text into HTML with direction marked as bidirectional.

    Args:
        body(str): Input text to wrap

    Returns:
        str: Text wrapped into <body> with dir='rtl' attribute
    """
    return f"<html><body dir='rtl'>{body}</body></html>"


class EmailUtils:

    def __init__(self, logger: ScriptLogger) -> None:
        self.logger = logger

    @staticmethod
    def is_attachment(
        mime_part: email.message.Message,
        include_inline: bool = False,
    ) -> bool:
        """Determine if a MIME part is a valid attachment or not. Based on :
        https://www.ietf.org/rfc/rfc2183.txt
        More about the content-disposition allowed fields and values:
        https://www.iana.org/assignments/cont-disp/cont-disp.xhtml#cont-disp-1
        Args:
            mime_part: {email.message.Message} The MIME part
            include_inline(bool): Whether to consider inline attachments as well or now.

        Returns:
            bool: True if MIME part is an attachment, False otherwise
        """
        content_disposition = mime_part.get("Content-Disposition")

        if not content_disposition or not isinstance(content_disposition, str):
            return False

        if content_disposition.lower().startswith("attachment"):
            return True

        if include_inline and content_disposition.lower().startswith("inline"):
            return True

        return False

    def convert_siemplify_ics_to_connector_msg(
        self,
        ics_content: str,
    ) -> MutableSequence[SingleJson]:
        """Converts Siemplify ICS content to a list of connector-compatible message
        dictionaries.

        Args:
            ics_content(str): The raw ICS content as a string.

        Returns:
            MutableSequence[SingleJson]: A list of dictionaries, where each dictionary
            represents an event from the ICS data, formatted for connector
            compatibility. Returns an empty list if no "vevent" components are found.
        """
        parsed_ics_attachments = []
        cal = Calendar.from_ical(ics_content)

        for component in cal.walk("vevent"):
            subject = get_unicode_str(component.get("summary", ""))
            body = get_unicode_str(component.get("description", ""))
            location = get_unicode_str(component.get("location", ""))
            start = (
                component.get("dtstart", "").dt.isoformat()
                if component.get("dtstart", "")
                else None
            )
            end = (
                component.get("dtend", "").dt.isoformat()
                if component.get("dtend", "")
                else None
            )
            message_id = MESSAGE_ID_FORMAT.format(component.get("uid", ""))
            organizer = component.get("organizer", "").replace(EMAIL_PREFIX, "")
            attendees_list = component.get("attendee", "")
            attendees_list = (
                [attendees_list] if isinstance(attendees_list, str) else attendees_list
            )
            attendees = DEFAULT_DIVIDER.join(
                [a.replace(EMAIL_PREFIX, "").strip() for a in attendees_list]
            )
            attachments_urls_list = self.extract_urls_from_ics_attachments(component)
            received_datetime = datetime.fromisoformat(start).strftime(
                constants.TIME_FORMAT
            )
            created_datetime = datetime.fromisoformat(end).strftime(
                constants.TIME_FORMAT
            )

            parsed_ics_attachment = {
                "subject": subject,
                "body": {"contentType": "text/plain", "content": body},
                "location": location,
                "receivedDateTime": received_datetime,
                "createdDateTime": created_datetime,
                "internetMessageId": message_id,
                "from": {"emailAddress": {"address": organizer}},
                "organizer": organizer,
                "toRecipients": [
                    {"emailAddress": {"address": attendee}}
                    for attendee in attendees.split(DEFAULT_DIVIDER)
                ],
                "attendees": attendees,
            }

            if attachments_urls_list:
                parsed_ics_attachment["urls"] = attachments_urls_list

            parsed_ics_attachments.append(parsed_ics_attachment)

        if not parsed_ics_attachments:
            self.logger.info(
                "Unable to find event for calender : "
                f"{cal.get('X-WR-CALNAME', 'Unknown')}"
            )

        return parsed_ics_attachments

    def extract_urls_from_ics_attachments(
        self,
        content: SingleJson,
    ) -> str:
        """Extracts URLs from ICS attachment data.

        Args:
            content(SingleJson): The ICS component containing attachment information.

        Returns:
            str: A string containing extracted URLs delimited by DEFAULT_LIST_DELIMITER,
            or an empty string if no URLs are found.
        """
        regex_object = re.compile(URLS_REGEX)
        attachments = content.get("attach", [])
        attachments = attachments if isinstance(attachments, list) else [attachments]
        attachments_list = [
            check_url_enclosing(url.strip(CHARS_TO_STRIP))
            for url in regex_object.findall(DEFAULT_LIST_DELIMITER.join(attachments))
            if "@" not in url
        ]
        return DEFAULT_LIST_DELIMITER.join(attachments_list)

    def extract_headers_value_from_message(
        self,
        msg: email.message.Message,
        headers: MutableSequence[str],
    ) -> MutableMapping[str, str]:
        """Extracts header values from an email message based on provided regex
        patterns.

        Args:
            msg(email.message.Message): The email message object.
            headers(MutableSequence[str]): A list of regex patterns to match against
            header keys.

        Returns:
            MutableMapping[str, str]: A dictionary containing the matched header keys
            and their values. Returns an empty dictionary if no headers are provided or
            no matches are found.
        """
        if headers and headers[0] == "None":
            return {}

        filtered_headers: MutableMapping[str, str] = {}
        header_keys = msg.keys()
        if not headers:
            for header in header_keys:
                _set_header_values(header, msg, filtered_headers)

        else:
            for header in headers:
                _set_header_values(header, msg, filtered_headers)

        return filtered_headers

    def extract_filename(self, mime_part: email.message.Message) -> str:
        """Extracts the filename of an attachment MIME part.

        Args:
            mime_part(email.message.Message): The MIME part.

        Returns:
            str: The decoded filename as a string, or None if the filename parameter is
            missing.
        """
        missing = object()

        filename = mime_part.get_param("filename", missing, "content-disposition")

        if filename is missing:
            filename = mime_part.get_param("name", missing, "content-disposition")

        if filename is missing:
            return None

        return decode_header_value(filename)

    def _extract_attachments_from_eml(
        self,
        msg: email.message.Message,
        encode_as_base64: bool = False,
        exclude_attachments: MutableSequence[str] | None = None,
    ) -> MutableMapping[str, str]:
        """Extracts attachments from an email.message.Message object (eml MIME).

        Args:
            msg(email.message.Message): The email message object.
            encode_as_base64(bool): Whether to encode attachment content as base64.
            exclude_attachments(MutableSequence[str]): A list of attachment filenames
            to exclude.

        Returns:
            MutableMapping[str, str]: A dictionary where keys are attachment filenames
            and values are their content (base64 encoded if encode_as_base64 is True).
            Nested messages are not supported.
        """
        attachments_dict: MutableMapping[str, str] = {}

        if msg.is_multipart():
            attachments = msg.get_payload()
            index = 0

            for attachment in attachments:
                if not self.is_attachment(attachment):
                    continue

                if attachment.get_content_type() == "message/rfc822":
                    filename, file_content, md5_file_hash = (
                        self._extract_nested_message(attachment)
                    )
                else:
                    filename, file_content, md5_file_hash = (
                        self._extract_regular_attachment(attachment, encode_as_base64)
                    )

                if exclude_attachments and filename in exclude_attachments:
                    continue

                attachments_dict.update(
                    {
                        f"attachment_name_{index}": filename,
                        f"base64_encoded_content_{index}": file_content,
                        f"md5_filehash_{index}": md5_file_hash,
                    }
                )
                index += 1

        return attachments_dict

    def _extract_nested_message(
        self,
        attachment: email.message.Message,
    ) -> tuple[str, str]:
        """Extracts content, filename, and MD5 hash from a nested message.

        Args:
            attachment(email.message.Message): The nested message attachment.

        Returns:
            tuple[str, str]: A tuple containing the filename, file content as a string,
            and the MD5 hash.
        """
        file_content = attachment.get_payload()[0].as_string()
        md5_file_hash = self._compute_md5_hash(file_content)
        filename = self.extract_subject(email.message_from_string(file_content))

        return filename, file_content, md5_file_hash

    def _extract_regular_attachment(
        self,
        attachment: email.message.Message,
        encode_as_base64: bool,
    ) -> tuple[str, str, str]:
        """Extracts filename, content, and MD5 hash for regular attachments.

        Args:
            attachment(email.message.Message): The attachment MIME part.
            encode_as_base64(bool): Whether to encode the content in base64.

        Returns:
            tuple[str, str, str]: A tuple containing the filename, content
            (base64 encoded if requested), and MD5 hash of the content.
            Handles .eml attachments as a special case.
        """
        filename = self.extract_filename(attachment)
        file_content = attachment.get_payload(decode=True)
        md5_file_hash = self._compute_md5_hash(file_content)

        if not file_content and ".eml" in filename:
            file_data = attachment.get_payload()[0]
            payload = file_data.get_payload()
            md5_file_hash = self._compute_md5_hash(payload)
            file_content = b64decode(payload)

        if encode_as_base64:
            file_content = b64encode(file_content).decode()

        return filename, file_content, md5_file_hash

    def _compute_md5_hash(self, content: bytes | str) -> str:
        """Computes the MD5 hash of the given content.

        Args:
            content(bytes | str): The content to hash (can be bytes or string).

        Returns:
            str: The MD5 hash as a hexadecimal string.
        """
        if isinstance(content, str):
            content = content.encode()

        return hashlib.md5(content).hexdigest()

    def convert_siemplify_eml_to_connector_eml(
        self,
        eml_content: bytes,
        encode_attachments_as_base64: bool = True,
        exclude_attachments: MutableSequence[str] | None = None,
        headers_to_add: MutableSequence[str] | None = None,
        smime_auth: SmimeAuth | None =None,
    ) -> SingleJson:
        """Converts a Siemplify EML object to a connector-compatible EML object.

        Args:
            eml_content(bytes): The raw EML content as bytes.
            encode_attachments_as_base64(bool): Whether to encode attachments as base64.
            exclude_attachments(MutableSequence[str] | None): A list of attachment
            filenames to exclude.
            headers_to_add(MutableSequence[str] | None: A list of header regex patterns
            to add.
            smime_auth(SmimeAuth | None): SmimeAuth object.

        Returns:
            SingleJson: A dictionary representing the connector-compatible EML object.
        """
        msg = email.message_from_bytes(eml_content)
        email_config = SmimeEmailConfig(
            email=msg,
            private_key_b64=smime_auth.private_key_b64,
            certificate_b64=smime_auth.certificate_b64,
            ca_certificate_b64=smime_auth.ca_certificate_b64,
        )
        msg = decrypt_email(email_config, logger=self.logger)

        metadata = self.convert_eml_to_siemplify_eml(msg)

        received_datetime = datetime.fromtimestamp(
            metadata.get(SIEMPLIFY_MAIL_DICT_UNIXTIME_DATE_KEY) / 1000.0
        )

        main_content = {
            "attachments": self._extract_attachments_from_eml(
                msg,
                encode_as_base64=encode_attachments_as_base64,
                exclude_attachments=exclude_attachments,
            ),
            "bccRecipients": [
                {"emailAddress": {"address": bcc_email}}
                for bcc_email in metadata.get(SIEMPLIFY_MAIL_DICT_BCC_KEY, [])
            ],
            "ccRecipients": [
                {"emailAddress": {"address": cc_email}}
                for cc_email in metadata.get(SIEMPLIFY_MAIL_DICT_CC_KEY, [])
            ],
            "body": {
                "contentType": "html",
                "content": metadata.get(SIEMPLIFY_MAIL_DICT_HTML_BODY_KEY),
            },
            "receivedDateTime": received_datetime.strftime(constants.TIME_FORMAT),
            "date": metadata.get(SIEMPLIFY_MAIL_DICT_DATE_KEY),
            "replyTo": [
                {
                    "emailAddress": {
                        "address": metadata.get(SIEMPLIFY_MAIL_DICT_IN_REPLY_TO_KEY)
                    }
                }
            ],
            "internetMessageId": metadata.get(SIEMPLIFY_MAIL_DICT_MESSAGE_ID_KEY),
            "uniqueBody": {
                "contentType": "text",
                "content": metadata.get(SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY),
            },
            "from": {
                "emailAddress": {
                    "address": metadata.get(SIEMPLIFY_MAIL_DICT_SENDER_KEY)
                }
            },
            "subject": metadata.get(SIEMPLIFY_MAIL_DICT_SUBJECT_KEY),
            "toRecipients": [
                {"emailAddress": {"address": recipient}}
                for recipient in metadata.get(SIEMPLIFY_MAIL_DICT_TO_KEY, [])
            ],
            SIEMPLIFY_MAIL_DICT_UNIXTIME_DATE_KEY: metadata.get(
                SIEMPLIFY_MAIL_DICT_UNIXTIME_DATE_KEY
            ),
        }
        main_content.update(
            self.extract_headers_value_from_message(msg, headers_to_add)
        )
        return main_content

    @staticmethod
    def extract_email_addresses_from_msg(
        message: email.message.Message,
        header_name: str,
    ) -> MutableSequence[str]:
        """Extracts email addresses from a message header.

        This function handles potential encoding issues and uses
        email.utils.getaddresses for robust address extraction.

        Args:
            message(email.message.Message): The email message.
            header_name(str): The name of the header containing email addresses.

        Returns:
            MutableSequence[str]: A list of extracted email addresses, excluding
            duplicates. Returns an empty list if the header is not found or empty.
        """

        def decode(text: bytes | str, encoding: str) -> str:
            """Decode a text. If an exception occurs when decoding returns the
            original text"""
            try:
                if isinstance(text, bytes):
                    return text.decode(encoding or "utf-8")

                return text

            except Exception:
                return text_to_utf8(text)

        header_value = message[header_name]

        if not header_value:
            return []

        if isinstance(header_value, str):
            header_value = header_value.replace("\n", " ")

        pieces = email.header.decode_header(header_value)
        pieces = [decode(text, encoding) for text, encoding in pieces]
        addresses = sorted(
            list(
                set(
                    e
                    for realname, e in email.utils.getaddresses(
                        ["".join(pieces).strip()]
                    )
                    if e
                )
            )
        )
        return [address for address in addresses if "@" in address]

    def convert_eml_to_siemplify_eml(
        self,
        msg: email.message.Message,
        include_raw_eml: bool = False,
        email_uid: str | None = None,
    ) -> SingleJson:
        """Creates a Siemplify-compatible EML object from an email.message.Message.

        Args:
            msg(email.message.Message): The email.message.Message object.
            include_raw_eml(bool): Whether to include the raw EML content.
            email_uid(str | None): Optional email UID.

        Returns:
            SingleJson: A dictionary representing the Siemplify-compatible EML object.
        """

        extractor = MetaData(msg)
        mail_dict = extractor.to_dict()

        mail_dict[SIEMPLIFY_MAIL_DICT_UNIXTIME_DATE_KEY] = (
            self.extract_unixtime_date_from_msg(msg.get("date"))
        )
        mail_dict[SIEMPLIFY_MAIL_DICT_DATE_KEY] = msg.get("date")

        subject = self.extract_subject(msg)

        if subject:
            subject = subject.strip()

        mail_dict[SIEMPLIFY_MAIL_DICT_SUBJECT_KEY] = (
            subject if subject else constants.EMPTY_SUBJECT
        )

        mail_dict[SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY] = (
            self.extract_bodies_from_eml(msg)[0]
        )
        mail_dict[SIEMPLIFY_MAIL_DICT_HTML_BODY_KEY] = self.extract_bodies_from_eml(
            msg,
        )[1]
        mail_dict[SIEMPLIFY_MAIL_DICT_EMAIL_ID_KEY] = email_uid

        if not mail_dict.get(SIEMPLIFY_MAIL_DICT_SENDER_KEY):
            mail_dict[SIEMPLIFY_MAIL_DICT_SENDER_KEY] = constants.UNKNOWN_SENDER
        if not mail_dict.get(SIEMPLIFY_MAIL_DICT_TO_KEY):
            mail_dict[SIEMPLIFY_MAIL_DICT_TO_KEY] = []
        if not mail_dict.get(SIEMPLIFY_MAIL_DICT_CC_KEY):
            mail_dict[SIEMPLIFY_MAIL_DICT_CC_KEY] = []
        if not mail_dict.get(SIEMPLIFY_MAIL_DICT_BCC_KEY):
            mail_dict[SIEMPLIFY_MAIL_DICT_BCC_KEY] = []

        if mail_dict[SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY]:
            mail_dict[SIEMPLIFY_MAIL_DICT_RESOLVED_BODY_KEY] = mail_dict[
                SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY
            ]
        else:
            mail_dict[SIEMPLIFY_MAIL_DICT_RESOLVED_BODY_KEY] = self.render_html_body(
                mail_dict[SIEMPLIFY_MAIL_DICT_HTML_BODY_KEY]
            )

        try:
            match = re.search(
                ANSWER_PLACEHOLDER_PATTERN,
                mail_dict[SIEMPLIFY_MAIL_DICT_RESOLVED_BODY_KEY],
            )
            if match:
                mail_dict[SIEMPLIFY_MAIL_DICT_ANSWER_ID_KEY] = match.group()
            else:
                mail_dict[SIEMPLIFY_MAIL_DICT_ANSWER_ID_KEY] = ""

        except Exception:
            mail_dict[SIEMPLIFY_MAIL_DICT_ANSWER_ID_KEY] = ""

        if include_raw_eml:
            mail_dict["original_message"] = msg.as_string()

        return mail_dict

    def extract_bodies_from_eml(
        self,
        msg: email.message.Message,
    ) -> tuple[str, str, int]:
        """Extracts plain text and HTML bodies from an email message.

        Args:
            msg(email.message.Message): The email.message.Message object.

        Returns:
            tuple[str, str, int]: A tuple containing the plain text body, HTML body,
            and the count of message parts.
        """
        html_body = ""
        text_body = ""
        count = 0

        if not msg.is_multipart() and not self.is_attachment(msg):
            content_type = msg.get_content_type()
            message_payload = msg.get_payload(decode=True)
            charset = get_charset(msg, "utf-8")

            if content_type == "text/plain":
                text_body += self.decode_by_charset(message_payload, charset)
            elif content_type == "text/html":
                html_body += self.decode_by_charset(message_payload, charset)

            return text_body, html_body, 1

        for part_msg in msg.get_payload():
            if not self.is_attachment(part_msg):
                part_text_body, part_html_body, part_count = (
                    self.extract_bodies_from_eml(part_msg)
                )
                text_body += part_text_body
                html_body += part_html_body
                count += part_count

        return text_body, html_body, count

    @staticmethod
    def decode_by_charset(
        bytes_string: bytes,
        charset: str,
        default_charset: str = "latin1",
    ) -> str:
        """Decodes a bytes string using the specified charset or a default.

        Args:
            bytes_string(bytes): The bytes string to decode.
            charset(str): The character set to use for decoding.
            default_charset(str): The default character set if the specified one fails.

        Returns:
            str: The decoded string.  If decoding fails with both charsets, returns
            the string decoded with the specified charset, ignoring errors.
        """
        try:
            return bytes_string.decode(charset)

        except Exception:
            try:
                return bytes_string.decode(default_charset)

            except Exception:
                return bytes_string.decode(charset, "ignore")

    def extract_subject(self, msg: email.message.Message) -> str:
        """Extracts the subject from an email message.

        Args:
            msg(email.message.Message): The email message object.

        Returns:
            str: The extracted subject as a string. Returns an empty string if the
            subject is missing or empty.
        """
        raw_subject = msg.get(MAIL_SUBJECT_KEY)

        return decode_header_value(raw_subject)

    @staticmethod
    def extract_unixtime_date_from_msg(
        date_str: str | None,
        default_value: int = 1,
    ) -> int:
        """Extracts the date of the message in Unix timestamp format.

        Args:
            date_str(str | None): The date string to parse.
            default_value(int): The default value to return if parsing fails.

        Returns:
            int: The Unix timestamp of the message (milliseconds). Returns the default
            value if parsing fails or date_str is None.
        """
        try:
            if date_str:
                date_tuple = email.utils.parsedate_tz(date_str)
                if date_tuple:
                    return email.utils.mktime_tz(date_tuple) * 1000

            return default_value

        except Exception:
            return default_value

    @staticmethod
    def _build_html_2_text_obj() -> html2text.HTML2Text:
        """Creates an HTML2Text object with specific configurations.

        Returns:
            html2text.HTML2Text: The configured HTML2Text object.
        """
        html_renderer = html2text.HTML2Text()
        html_renderer.ignore_tables = True
        html_renderer.protect_links = True
        html_renderer.ignore_images = False
        html_renderer.ignore_links = False

        return html_renderer

    @classmethod
    def render_html_body(cls, html_body: str) -> str:
        """Renders an HTML body to plain text.

        Args:
            html_body(str): The HTML content to render.

        Returns:
            str: The rendered plain text string.  If rendering fails, returns an error
            message string.
        """
        try:
            html_renderer = cls._build_html_2_text_obj()
            return html_renderer.handle(html_body)

        except Exception:
            try:
                html_renderer = cls._build_html_2_text_obj()
                html_body = html_body.decode("utf8")

                return html_renderer.handle(html_body).encode("utf8")

            except Exception as e:
                return f"Failed rendering HTML. Error: {str(e)}"

    def convert_siemplify_msg_to_connector_msg(
        self,
        msg_content: bytes,
        headers_to_add: list[str] | None = None,
    ) -> SingleJson | None:
        """Converts a Siemplify MSG object to a connector-compatible MSG object.

        Args:
            msg_content(bytes): The raw MSG content as bytes.
            headers_to_add(list[str] | None): A list of header regex patterns to add.

        Returns:
            SingleJson | None: A dictionary representing the connector-compatible MSG
            object, or None if parsing fails.
        """
        try:
            msg = extract_msg.Message(BytesIO(msg_content))
            metadata = self.convert_outlook_msg_to_siemplify_msg(msg=msg)

            main_content = {
                "answer": metadata.get(SIEMPLIFY_MAIL_DICT_ANSWER_ID_KEY),
                "attachments": self._extract_attachment_from_outlook_msg(
                    msg=msg,
                    encode_as_base64=True,
                ),
                "bccRecipients": [
                    {"emailAddress": {"address": bcc_email}}
                    for bcc_email in metadata.get(SIEMPLIFY_MAIL_DICT_BCC_KEY, [])
                ],
                "ccRecipients": [
                    {"emailAddress": {"address": cc_email}}
                    for cc_email in metadata.get(SIEMPLIFY_MAIL_DICT_CC_KEY, [])
                ],
                "body": {
                    "contentType": "html",
                    "content": metadata.get(SIEMPLIFY_MAIL_DICT_HTML_BODY_KEY),
                },
                "receivedDateTime": metadata.get(SIEMPLIFY_MAIL_DICT_DATE_KEY),
                "replyTo": [
                    {
                        "emailAddress": {
                            "address": metadata.get(SIEMPLIFY_MAIL_DICT_IN_REPLY_TO_KEY)
                        }
                    }
                ],
                "internetMessageId": metadata.get(SIEMPLIFY_MAIL_DICT_MESSAGE_ID_KEY),
                "uniqueBody": {
                    "contentType": "text",
                    "content": metadata.get(SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY),
                },
                "from": {
                    "emailAddress": {
                        "address": metadata.get(SIEMPLIFY_MAIL_DICT_SENDER_KEY)
                    }
                },
                "subject": metadata.get(SIEMPLIFY_MAIL_DICT_SUBJECT_KEY),
                "toRecipients": [
                    {"emailAddress": {"address": recipient}}
                    for recipient in metadata.get(SIEMPLIFY_MAIL_DICT_TO_KEY, [])
                ],
            }
            main_content.update(
                self.extract_headers_value_from_message(msg.header, headers_to_add)
            )

            return main_content

        except (OleFileError, ExMsgBaseException) as e:
            self.logger.error(f"Failed to parse MSG content: {e}")
            return None

    def convert_outlook_msg_to_siemplify_msg(
        self,
        msg: extract_msg.Message,
        email_uid: str | None = None,
    ) -> SingleJson:
        """Creates a Siemplify MSG object from an Outlook MSG object.

        Args:
            msg(extract_msg.Message,): The extract_msg.Message object.
            email_uid(str | None): Optional email UID.

        Returns:
            SingleJson: A dictionary representing the Siemplify MSG object.
        """
        mail_dict = {}
        EmailUtils.replaced_msg_header_unsupported_encoding(msg, "from")
        EmailUtils.replaced_msg_header_unsupported_encoding(msg, "to")
        EmailUtils.replaced_msg_header_unsupported_encoding(msg, "cc")
        EmailUtils.replaced_msg_header_unsupported_encoding(msg, "bcc")
        mail_dict[SIEMPLIFY_MAIL_DICT_UNIXTIME_DATE_KEY] = (
            self.extract_unixtime_date_from_msg(msg.date)
        )
        mail_dict[SIEMPLIFY_MAIL_DICT_DATE_KEY] = datetime(*msg.parsedDate[0:6])
        mail_dict[SIEMPLIFY_MAIL_DICT_TIMESTAMP_KEY] = int(time.mktime(msg.parsedDate))
        mail_dict[SIEMPLIFY_MAIL_DICT_SENDER_KEY] = self.extract_addresses(
            msg.sender or ""
        )
        mail_dict[SIEMPLIFY_MAIL_DICT_TO_KEY] = self.extract_addresses(msg.to)
        mail_dict[SIEMPLIFY_MAIL_DICT_CC_KEY] = self.extract_addresses(msg.cc)
        mail_dict[SIEMPLIFY_MAIL_DICT_BCC_KEY] = self.extract_addresses(
            msg.header.get("bcc")
        )
        mail_dict[SIEMPLIFY_MAIL_DICT_REPLY_TO_KEY] = msg.inReplyTo
        mail_dict[SIEMPLIFY_MAIL_DICT_IN_REPLY_TO_KEY] = msg.inReplyTo
        mail_dict[SIEMPLIFY_MAIL_DICT_MESSAGE_ID_KEY] = msg.messageId
        mail_dict[SIEMPLIFY_MAIL_DICT_EMAIL_ID_KEY] = email_uid
        mail_dict[SIEMPLIFY_MAIL_DICT_DISPLAY_NAME_KEY] = self.extract_names(
            msg.sender or ""
        )

        mail_dict[SIEMPLIFY_MAIL_DICT_RECEIVERS_KEY] = set()
        mail_dict[SIEMPLIFY_MAIL_DICT_RECEIVERS_KEY].union(
            mail_dict[SIEMPLIFY_MAIL_DICT_TO_KEY]
        )
        mail_dict[SIEMPLIFY_MAIL_DICT_RECEIVERS_KEY].union(
            mail_dict[SIEMPLIFY_MAIL_DICT_CC_KEY]
        )
        mail_dict[SIEMPLIFY_MAIL_DICT_RECEIVERS_KEY].union(
            mail_dict[SIEMPLIFY_MAIL_DICT_BCC_KEY]
        )
        mail_dict[SIEMPLIFY_MAIL_DICT_SUBJECT_KEY] = get_unicode_str(msg.subject)
        mail_dict[SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY] = get_unicode_str(msg.body)

        try:
            mail_dict[SIEMPLIFY_MAIL_DICT_HTML_BODY_KEY] = (
                self.extract_html_body_from_outlook_msg(msg)
            )
        except Exception as e:
            mail_dict[SIEMPLIFY_MAIL_DICT_HTML_BODY_KEY] = (
                f"Unable to extract HTML body. Error: {e}"
            )
        if mail_dict[SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY]:
            mail_dict[SIEMPLIFY_MAIL_DICT_RESOLVED_BODY_KEY] = mail_dict[
                SIEMPLIFY_MAIL_DICT_PLAINTEXT_BODY_KEY
            ]
        else:
            mail_dict[SIEMPLIFY_MAIL_DICT_RESOLVED_BODY_KEY] = self.render_html_body(
                mail_dict[SIEMPLIFY_MAIL_DICT_HTML_BODY_KEY]
            )

        try:
            match = re.search(
                ANSWER_PLACEHOLDER_PATTERN,
                mail_dict[SIEMPLIFY_MAIL_DICT_RESOLVED_BODY_KEY],
            )
            if match:
                mail_dict[SIEMPLIFY_MAIL_DICT_ANSWER_ID_KEY] = match.group()
            else:
                mail_dict[SIEMPLIFY_MAIL_DICT_ANSWER_ID_KEY] = ""
        except Exception:
            mail_dict[SIEMPLIFY_MAIL_DICT_ANSWER_ID_KEY] = ""

        return mail_dict

    @staticmethod
    def replaced_msg_header_unsupported_encoding(
        msg: extract_msg.Message,
        header_key: str,
        unsupported_encoding: str | None = None,
        supported_encoding: str | None = None,
    ) -> None:
        """Replaces an unsupported encoding in a message header with a supported one.

        Args:
            msg (email.message.Message): The email message object.
            key (str): The header key to check and modify.
            e.g.: "from", "to", "cc", "bcc", "subject"
            unsupported_encoding (str | None): unsupported encoding to be replaced.
            supported_encoding (str | None): supported encoding to be used.
        """
        unsupported_encoding = unsupported_encoding or "iso-8859-8-i"
        supported_encoding = supported_encoding or "iso-8859-8"
        value_from_header = msg.header.get(header_key)

        if value_from_header is not None:
            if unsupported_encoding in value_from_header:
                msg.header.replace_header(
                    header_key,
                    value_from_header.replace(unsupported_encoding, supported_encoding),
                )

    @staticmethod
    def extract_html_body_from_outlook_msg(msg: extract_msg.Message) -> str:
        """Extracts the HTML body from an Outlook MSG object.

        Args:
            msg(extract_msg.Message): The extract_msg.Message object.

        Returns:
            str: The extracted HTML body as a string. If no HTML body is available
            and conversion from RTF fails, returns an empty string.
        """
        if msg.htmlBody:
            return get_unicode_str(msg.htmlBody)

        rtf_content = compressed_rtf.decompress(msg.compressedRtf)
        rtf_file = BytesIO()
        rtf_file.write(rtf_content)

        rdf_handler = Rtf15Reader.read(rtf_file)
        html_body = XHTMLWriter.write(rdf_handler, pretty=True).read()

        return get_unicode_str(html_body)

    @staticmethod
    def extract_addresses_with_names(
        header_content: str,
    ) -> MutableMapping[str, str | None]:
        """Extracts email addresses and display names from an email header.

        Args:
            header_content(str): The header content string.

        Returns:
            MutableMapping[str, str | None]: A dictionary mapping email addresses to
            display names (or None if no display name is found). Returns an empty
            dictionary if the header content is empty or None.
        """

        def decode(text: bytes | str, encoding: str | None) -> str:
            """Decodes text using the provided encoding or UTF-8 if encoding is None.

            Args:
                text: (bytes | str): The text to decode (can be bytes or str).
                encoding(str | None): The encoding to use, or None to default to UTF-8.

            Returns:
                str: The decoded string. If decoding fails, it returns the unicode str.
            """
            if encoding is None:
                return get_unicode_str(text)
            try:
                return text.decode(encoding)
            except Exception:
                return get_unicode_str(text)

        result: MutableMapping[str, str | None] = {}
        pieces = email.header.decode_header(header_content or "")
        pieces = [decode(text, encoding) for text, encoding in pieces]
        header_value = "".join(pieces).strip()
        name, address = email.utils.parseaddr(header_value)
        while address:
            result[address] = name or None
            index = header_value.find(address) + len(address)
            if index >= len(header_value):
                break
            if header_value[index] == ">":
                index += 1
            if index >= len(header_value):
                break
            if header_value[index] == ",":
                index += 1
            header_value = header_value[index:].strip()
            name, address = email.utils.parseaddr(header_value)

        return result

    def extract_addresses(self, header_content: str) -> MutableSequence[str]:
        """Extracts email addresses from an email header.

        Args:
            header_content(str): The header content string.

        Returns:
            MutableSequence[str]: A list of extracted email addresses. Returns an empty
            list if the header content is empty or None.
        """
        result = self.extract_addresses_with_names(header_content)
        return [address for address in result if address and address != str(None)]

    def extract_names(self, header_content: str) -> MutableSequence[str]:
        """Extracts display names from an email header.

        Args:
            header_content(str): The header content string.

        Returns:
            MutableSequence[str]: A list of extracted display names. Returns an empty
            list if the header content is empty, None, or contains no display names.
        """

        result = self.extract_addresses_with_names(header_content)
        return [name for name in result.values() if name and name != str(None)]

    def _extract_attachment_from_outlook_msg(
        self,
        msg: extract_msg.Message,
        encode_as_base64: bool = False,
        convert_utf8: bool = True,
    ) -> MutableMapping[str, bytes | str]:
        """Extracts attachments from an Outlook MSG object.

        Args:
            msg(extract_msg.Message): The extract_msg.Message object.
            encode_as_base64(bool): Whether to base64 encode attachment content.
            convert_utf8(bool): Whether to UTF-8 encode filenames.


        Returns:
            MutableMapping[str, bytes | str]: A dictionary where keys are attachment
            filenames and values are either bytes (if encode_as_base64 is False)
            or base64 encoded strings (if encode_as_base64 is True). Includes a
            placeholder message for unsupported nested MSG attachments.
        """
        attachments_dict: MutableMapping[str, bytes | str] = {}

        for attachment in msg.attachments:
            if attachment.type.value == 0:
                if convert_utf8:
                    filename = attachment.longFilename.encode("utf8")
                else:
                    filename = attachment.longFilename

                file_content = attachment.data

                if encode_as_base64:
                    file_content = b64encode(file_content)

                attachments_dict.update({filename: file_content})
            else:
                attachments_dict.update(
                    {get_unicode_str(attachment.data.subject): INNER_MSG_NOT_SUPPORTED}
                )

        return attachments_dict

    @staticmethod
    def extract_regex_from_content(
        content: str,
        regex_map: MutableMapping[str, str],
    ) -> MutableMapping[str, str]:
        """Extracts fields from email body content using regular expressions.

        Args:
            content(str): The email body content string.
            regex_map(MutableMapping[str, str]): A dictionary mapping field names to
            regex patterns.

        Returns:
            MutableMapping[str, str]: A dictionary containing the extracted fields.
            If a regex for a default field (urls, subject, from, to) finds multiple
            matches, they are joined with the appropriate delimiter. For custom
            regexes, multiple matches are added as separate keys with an index suffix.
        """
        result_dictionary: MutableMapping[str, str] = {}

        for key, regex_value in regex_map.items():
            regex_object = re.compile(regex_value)
            all_results = regex_object.findall(content)
            if key in constants.DEFAULT_REGEX_MAP:
                if all_results:
                    if key == "urls":
                        all_results = [
                            check_url_enclosing(result) for result in all_results
                        ]
                        result_dictionary[key] = (
                            constants.DEFAULT_URLS_LIST_DELIMITER.join(all_results)
                        )
                    else:
                        result_dictionary[key] = constants.DEFAULT_LIST_DELIMITER.join(
                            all_results
                        )
            else:
                for index, result in enumerate(all_results, 1):
                    key_name = f"{key}_{index}" if len(all_results) > 1 else key
                    result_dictionary[key_name] = get_unicode_str(result)

        return result_dictionary

    @staticmethod
    def is_graph_mail_id(mail_id: str) -> bool:
        """Determine if the given string is a mail id or internet Message ID.

        Args:
            id (str): The string to be checked.

        Returns:
            bool: Returns True if the string is an internet message ID "
                else Returns False.
        """
        return re.match(constants.MESSAGE_ID_PATTERN, mail_id)


def get_decrypted_mime_content(
    mime_content: bytes,
    smime_auth: SmimeAuth,
    logger: ScriptLogger,
) -> bytes:
    """Decrypts a MIME content using S/MIME.

    Args:
        mime_content (bytes): The MIME content to decrypt.
        private_key_b64 (str): The base64 encoded private key.
        certificate_b64 (str): The base64 encoded certificate.
        ca_certificate_b64 (str): The base64 encoded CA certificate.
        logger (ScriptLogger): The logger instance.

    Returns:
        bytes: The decrypted MIME content as bytes.
    """
    msg: email.message.Message = email.parser.BytesParser(
        policy=email.policy.default
    ).parsebytes(text=mime_content)
    email_config: SmimeEmailConfig = SmimeEmailConfig(
        email=msg,
        private_key_b64=smime_auth.private_key_b64,
        certificate_b64=smime_auth.certificate_b64,
        ca_certificate_b64=smime_auth.ca_certificate_b64,
    )

    return decrypt_email(email_config, logger).as_bytes()


def _set_header_values(
    header: str,
    msg: email.message.Message,
    filtered_headers: SingleJson
) -> None:
    """
    Set header values in filtered_headers dictionary.

    Args:
        header (str): header name to be added to the event.
        msg (email.message.Message): message object.
        filtered_headers (SingleJson): dictionary to store header values.
    """
    header_regex = re.compile(header)
    header_keys = msg.keys()
    matched_keys = list(filter(header_regex.match, header_keys))
    for key in matched_keys:
        value = msg.get(key)
        filtered_headers[key] = _get_header_value(value)

def _get_header_value(value: str) -> str:
    if isinstance(value, str) and is_encoded_header(value):
        return decode_header_string(value)

    return str(value)

def is_encoded_header(header_value: str) -> bool:
    decoded_parts = email.header.decode_header(header_value)
    return any(isinstance(part, bytes) for part, encoding in decoded_parts if encoding)


def decode_header_string(header_value: str) -> str:
    """Decodes a header string that may contain RFC 2047 encoded-words.

    This function handles header values that are encoded according to RFC 2047.
    It decodes each part of the header, handling various encodings and potential
    decoding errors. It then concatenates the decoded parts into a single string.

    Args:
        header_value (str): The header value to decode.

    Returns:
        str: The decoded header string.
    """
    header_value = header_value.replace("\r\n", "")
    decoded_header_parts = email.header.decode_header(header_value)
    decoded_parts = []
    for part, encoding in decoded_header_parts:
        if isinstance(part, bytes):
            try:
                part = part.decode(encoding or "raw-unicode-escape")

            except LookupError:
                encoding = encoding.rstrip("-i").rstrip("-I")
                part = part.decode(encoding)

        decoded_parts.append(part)

    return "".join(decoded_parts)

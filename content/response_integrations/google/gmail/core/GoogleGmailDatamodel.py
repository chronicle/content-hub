# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import enum
import hashlib
from datetime import datetime
from typing import Any, Callable

import copy
import base64
import json
import dataclasses
import os
import re

import pydantic
from pydantic.alias_generators import to_camel

from soar_sdk.SiemplifyDataModel import Attachment
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import SingleJson

from gmail.core.GoogleGmailConsts import DATETIME_FORMAT, DEFAULT_MAILBOX, REGEX_DATETIME_STR
from gmail.core.GoogleGmailUtils import extract_email


class MailboxReadEnum(enum.Enum):
    READ = "Only Read Messages"
    UNREAD = "Only Unread Messages"
    BOTH = "Both Read & Unread Messages"


class MailboxProcessingStatus(enum.Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


@dataclasses.dataclass
class MailboxProcessingInfo:
    mailbox_name: str
    status: MailboxProcessingStatus = MailboxProcessingStatus.PENDING
    found_emails: int | None = None
    finished_emails: int = 0
    finished_operations_data: list[SingleJson] = dataclasses.field(default_factory=list)
    extra_context: SingleJson = None

    def result_is_already_processed(
            self,
            result: SingleJson,
            extraction_func: Callable[[SingleJson], str]
    ) -> bool:
        """Using extraction function check if the result already exists."""
        trial_value = extraction_func(result)
        return any(
            trial_value == extraction_func(result_)
            for result_ in self.finished_operations_data
        )

    def set_finished_operations(
            self,
            results: tuple[SingleJson | str | None],
    ) -> None:
        """Set finished operations list with successful results."""
        finished_operations = tuple(
            result for result in results
            if not isinstance(result, BaseException)
        )
        self.finished_emails = len(finished_operations)
        self.finished_operations_data = [
            result for result in finished_operations if result is not None
        ]

    def extend_finished_operations(
            self,
            results: tuple[SingleJson | str | None],
    ) -> None:
        """Extend finished operations list with successful results."""
        finished_operations = tuple(
            result for result in results
            if not isinstance(result, BaseException)
        )
        self.finished_emails += len(finished_operations)
        self.finished_operations_data.extend(
            result for result in finished_operations if result is not None
        )

    def as_dict(self) -> SingleJson:
        return {
            field.name: (
                getattr(self, field.name).value if
                field.name == "status" else getattr(self, field.name)
            )
            for field in dataclasses.fields(self)
            if getattr(self, field.name) is not None
        }

    @classmethod
    def from_dict(cls, data: SingleJson) -> MailboxProcessingInfo:
        return cls(
            mailbox_name=data["mailbox_name"],
            status=MailboxProcessingStatus[data["status"]],
            found_emails=data.get("found_emails"),
            finished_emails=data.get("finished_emails"),
            finished_operations_data=data["finished_operations_data"],
            extra_context=data.get("extra_context")
        )


@dataclasses.dataclass
class AsyncMailboxesActionContext:
    """Object that holds information to be passed between async action iterations."""
    mailboxes: dict[str, MailboxProcessingInfo]

    @property
    def unfinished_mailboxes(self) -> list[str]:
        return [
            mailbox.mailbox_name for mailbox in self.mailboxes.values()
            if mailbox.status in (
                MailboxProcessingStatus.PENDING,
                MailboxProcessingStatus.STARTED
            )
        ]

    @property
    def failed_mailboxes(self) -> list[str]:
        return [
            mailbox.mailbox_name for mailbox in self.mailboxes.values()
            if mailbox.status == MailboxProcessingStatus.FAILED
        ]

    @property
    def processed_mailboxes(self) -> list[MailboxProcessingInfo]:
        return [
            mailbox for mailbox in self.mailboxes.values()
            if mailbox.status in (
                MailboxProcessingStatus.FINISHED,
                MailboxProcessingStatus.STARTED and mailbox.finished_operations_data
            )
        ]

    def mark_mailbox_as_started(
            self,
            mailbox_name: str,
            found_emails: int
    ) -> None:
        """Mark the mailbox as started processing."""
        if self.mailboxes[mailbox_name].status == MailboxProcessingStatus.STARTED:
            return

        self.mailboxes[mailbox_name].status = MailboxProcessingStatus.STARTED
        self.mailboxes[mailbox_name].found_emails = found_emails

    def mark_mailbox_as_partially_finished(
            self,
            mailbox_name: str,
            results: tuple[SingleJson | str | Exception],
            overwrite: bool = False
    ) -> None:
        """Mark the mailbox as partially processed."""
        self.mailboxes[mailbox_name].status = MailboxProcessingStatus.STARTED
        if overwrite is True:
            self.mailboxes[mailbox_name].set_finished_operations(results)
            return

        self.mailboxes[mailbox_name].extend_finished_operations(results)

    def mark_mailbox_as_finished(
            self,
            mailbox_name: str,
            results: tuple[SingleJson | str | Exception],
            overwrite: bool = False
    ) -> None:
        """Mark mailbox as processed."""
        self.mailboxes[mailbox_name].status = MailboxProcessingStatus.FINISHED
        if overwrite is True:
            self.mailboxes[mailbox_name].set_finished_operations(results)
            return

        self.mailboxes[mailbox_name].extend_finished_operations(results)

    def mark_mailbox_as_failed(self, mailbox_name: str) -> None:
        """Mark mailbox as failed processing."""
        self.mailboxes[mailbox_name].status = MailboxProcessingStatus.FAILED

    @classmethod
    def from_mailboxes(
            cls,
            mailboxes: list[str],
            default_mailbox: str,
    ) -> AsyncMailboxesActionContext:
        """Resolve mailboxes and populate mailbox processing info per each."""
        mailboxes_ = {
            mailbox.lower() if mailbox != DEFAULT_MAILBOX else default_mailbox.lower()
            for mailbox in mailboxes
        }
        return cls(
            mailboxes={
                mailbox_name: MailboxProcessingInfo(mailbox_name=mailbox_name)
                for mailbox_name in mailboxes_
            }
        )

    def as_json(self) -> str:
        return json.dumps([mailbox.as_dict() for mailbox in self.mailboxes.values()])

    @classmethod
    def from_json(cls, json_str: str) -> AsyncMailboxesActionContext:
        mailboxes_json = json.loads(json_str)
        return cls(
            mailboxes={
                mailbox_json["mailbox_name"]: (
                    MailboxProcessingInfo.from_dict(mailbox_json)
                )
                for mailbox_json in mailboxes_json
            }
        )


class BaseGmailModel(pydantic.BaseModel):
    raw_data: dict[str, Any] | None = None

    def __init__(
            self,
            /,
            **kwargs,
    ) -> None:
        super().__init__(raw_data=kwargs, **kwargs)

    class Config:
        alias_generator = to_camel
        populate_by_name = True

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())


class GmailLabel(BaseGmailModel):
    id: str
    name: str
    type: str | None = None


class GmailMessagePartBody(BaseGmailModel):
    size: int
    attachment_id: str = None
    data: str | None = None

    _body_decoded: bytes | None = None

    @property
    def body_decoded(self) -> bytes | None:
        """Return decoded body of an email."""
        if self.data is None:
            return None

        if self._body_decoded is None:
            self._body_decoded = base64.urlsafe_b64decode(self.data)

        return self._body_decoded

    def to_json(self):
        """Prepare JSON serialized data."""
        json_data = {
            "size": self.size
        }

        if self.attachment_id is not None:
            json_data["attachmentId"] = self.attachment_id
            return json_data

        if self.data is not None:
            json_data["data"] = self.body_decoded.decode()

        return json_data


class GmailMessagePart(BaseGmailModel):
    part_id: str | None = None
    body: GmailMessagePartBody | None = None
    mime_type: str = ""
    filename: str = ""
    headers: list[dict[str, str]] = pydantic.Field(default_factory=list)
    parts: list["GmailMessagePart"] | None = None

    _headers_lookup: dict[str, list[str] | str] | None = None
    _text_bodies: list[str] | None = None
    _html_bodies: list[str] | None = None

    def is_attachment(self) -> bool:
        return bool(self.filename)

    @property
    def all_recipients(self) -> list[str]:
        """Merge all email recipients throughout to, cc and bcc headers."""
        all_recipients = []
        for field in ["to", "cc", "bcc"]:
            mails = self.parse_emails_list(
                self.get_field_from_headers(field)
            )
            all_recipients.extend(extract_email(mail).strip() for mail in mails)

        return all_recipients

    @property
    def sha1_hash(self) -> str | None:
        if self.filename and self.body.body_decoded:
            return hashlib.sha1(self.body.body_decoded).hexdigest()
        return None

    @property
    def base_64_encoded_body(self) -> str:
        return base64.b64encode(self.body.body_decoded).decode()

    def create_case_wall_attachment_object(self) -> Attachment:
        """Create attachment object for SOAR case wall."""
        file_name, file_extension = os.path.splitext(self.filename)
        return Attachment(
            case_identifier=None,
            alert_identifier=None,
            base64_blob=self.base_64_encoded_body,
            attachment_type=file_extension,
            name=file_name,
            description="This is an email attachment",
            is_favorite=False,
            orig_size=len(self.body.body_decoded),
            size=len(self.base_64_encoded_body),
        )

    @property
    def text_bodies(self) -> list[str]:
        """Extract text bodies from all message parts."""
        if self._text_bodies is None:
            self._text_bodies = []

            if self.mime_type == "text/plain":
                self._text_bodies.append(self.body.body_decoded.decode())

            for part in (self.parts or []):
                self._text_bodies.extend(part.text_bodies)

        return self._text_bodies

    @property
    def html_bodies(self) -> list[str]:
        """Extract html bodies from all message parts."""
        if self._html_bodies is None:
            self._html_bodies = []

            if self.mime_type == "text/html":
                self._html_bodies.append(self.body.body_decoded.decode())

            for part in (self.parts or []):
                self._html_bodies.extend(part.html_bodies)

        return self._html_bodies

    @property
    def file_attachments(self) -> list["GmailMessagePart"]:
        """Collect file attachments from this message, includes all embedded."""
        file_attachments = []
        if self.is_attachment():
            file_attachments.append(self)

        for part in (self.parts or []):
            file_attachments.extend(part.file_attachments)

        return file_attachments

    @property
    def headers_lookup(self) -> dict[str, str | list[str]]:
        """Email headers lookup dictionary."""
        if self._headers_lookup is None:
            self._headers_lookup = {}
            headers = (
                self.parts[0].headers
                if ".eml" in self.filename and self.parts
                else self.headers
            )

            for header in headers:
                header_name = header["name"].casefold()
                if header_name not in self._headers_lookup:
                    self._headers_lookup[header_name] = header["value"]
                    continue

                if not isinstance(self._headers_lookup[header_name], list):
                    self._headers_lookup[header_name] = [
                        self._headers_lookup[header_name]
                    ]

                self._headers_lookup[header_name].append(header["value"])

        return self._headers_lookup

    def get_field_from_headers(self, field_value: str) -> str:
        return self.headers_lookup.get(field_value, "")

    @staticmethod
    def parse_emails_list(emails_csv: str = "") -> list[str]:
        """Parse CSV of identities into a list of email addresses."""
        if not emails_csv:
            return []

        return [extract_email(email) for email in emails_csv.split(",")]

    @property
    def from_(self) -> str:
        """Extract from email address from headers."""
        return extract_email(self.get_field_from_headers("from"))

    @property
    def subject(self):
        return self.get_field_from_headers("subject")

    @property
    def message_id(self):
        return self.get_field_from_headers("message-id")

    @property
    def date(self) -> int:
        """Extract date from "Date email header and convert to timestamp."""
        date_match = re.search(
            REGEX_DATETIME_STR,
            self.get_field_from_headers("date")
        )
        if date_match is None:
            return 0

        return int(
            datetime.strptime(date_match.group(), DATETIME_FORMAT).timestamp()
        )

    def to_json(self, headers_list: list[str] | None = None) -> SingleJson:
        """Marshall the object into a JSON dict."""
        headers = (
            self.headers_lookup if not headers_list
            else {
                k: v for k, v in self.headers_lookup.items()
                if k in {header.casefold() for header in headers_list}
            }
        )
        return {
            "message_id": self.message_id,
            "subject": self.subject,
            "headers": headers,
            "mimetype": self.mime_type,
            "text_bodies": self.text_bodies,
            "html_bodies": self.html_bodies,
            "file_attachments": [
                p.filename for p in self.file_attachments
            ],
            "date": self.date,
            "from": self.from_,
            "to": ",".join(self.parse_emails_list(self.get_field_from_headers("to"))),
            "cc": ",".join(self.parse_emails_list(self.get_field_from_headers("cc"))),
            "bcc": ",".join(self.parse_emails_list(self.get_field_from_headers("bcc"))),
            "in-reply-to": self.get_field_from_headers("in-reply-to"),
            "reply-to": ",".join(
                self.parse_emails_list(self.get_field_from_headers("reply-to"))
            ),
        }

    def create_event(
            self,
            additional_info: dict[str, str],
            headers_to_add_to_events: list[str] | None = None,
    ):
        """Build SOAR event out of GmailMessage object."""
        event_data = copy.deepcopy(self.to_json(headers_to_add_to_events))
        event_data.update(additional_info)
        return dict_to_flat({
            k: v for k, v in event_data.items() if v is not None
        })


class GmailMessage(BaseGmailModel):
    id: str
    thread_id: str
    payload: GmailMessagePart | None = None
    snippet: str = ""
    history_id: str = ""
    internal_date: int = 0
    label_ids: list[str] = pydantic.Field(default_factory=list)

    _mime_content: bytes = None

    @property
    def alert_id(self) -> str:
        if self.payload and self.payload.message_id:
            return self.payload.message_id
        return self.id

    @property
    def mime_content(self) -> bytes:
        return self._mime_content

    @mime_content.setter
    def mime_content(self, value: bytes) -> None:
        self._mime_content = base64.urlsafe_b64decode(value)

    def create_case_wall_attachment_object(self) -> Attachment:
        """Create attachment object for SOAR case wall."""
        encoded_body = base64.b64encode(self.mime_content).decode()
        return Attachment(
            case_identifier=None,
            alert_identifier=None,
            base64_blob=encoded_body,
            attachment_type=".eml",
            name=self.payload.subject,
            description="This is the original message as EML",
            is_favorite=False,
            orig_size=len(self.mime_content),
            size=len(encoded_body),
        )

    def to_json(self, add_mime_content: bool = False) -> SingleJson:
        """Create JSON from Gmail Message metadata."""
        json_ = {
            "id": self.id,
            "thread_id": self.thread_id,
            "label_ids": self.label_ids,
            "snippet": self.snippet,
            "history_id": self.history_id,
            "internal_date": self.internal_date // NUM_OF_MILLI_IN_SEC
        }
        if add_mime_content:
            json_["mime_content"] = base64.b64encode(self.mime_content).decode()

        return json_

    @staticmethod
    def csv_from_json(json_: SingleJson, mailbox_name: str) -> dict[str, str]:
        """Build flat dict with values for a csv table."""
        return {
            "Message ID": json_["message_id"],
            "Received Date": json_["date"],
            "Sender": json_["from"],
            "Recipients": json_["to"].replace(",", ";"),
            "Subject": json_["subject"],
            "Email Body Snippet": json_["snippet"],
            "Attachment names": ";".join(json_["file_attachments"]),
            "Found in mailbox": mailbox_name,
        }

    def matches_exclude_pattern(self, exclude_pattern: str) -> bool:
        """Checks if message matches exclude patterns.

        Args:
            exclude_pattern: {str} Regex pattern, which would exclude emails with
                matching subject or body.

        Returns:
            {bool} True if matches one of the exclude patterns; False - otherwise.
        """

        if self.payload.subject and re.findall(exclude_pattern, self.payload.subject):
            return True

        bodies = self.payload.html_bodies + self.payload.text_bodies
        for body in bodies:
            if re.findall(exclude_pattern, body):
                return True

        return False


class GmailThread(BaseGmailModel):
    id: str
    history_id: str
    messages: list[GmailMessage]
    snippet: str | None = None

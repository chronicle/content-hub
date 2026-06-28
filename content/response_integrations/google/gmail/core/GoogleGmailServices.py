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

"""This module defines 'Services' - helper classes dedicated to wrap all Gmail related
business logic, such as creating 'Send', 'Forward', 'Reply' email MIME objects,
building proper use case specific API queries."""
from __future__ import annotations

from __future__ import annotations

import asyncio
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.parser import BytesParser

from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.smp_time import unix_now

from gmail.core.GoogleGmailApiManager import GoogleGmailApiManager
from gmail.core.GoogleGmailConsts import FORWARD_EMAIL_TEMPLATE
from gmail.core.GoogleGmailDatamodel import (
    GmailMessage,
    GmailMessagePart,
    GmailLabel,
    GmailThread,
    MailboxReadEnum,
)
from gmail.core.GoogleGmailUtils import (
    get_payload_decoded,
    set_attachments,
    set_body,
)

SECONDS_IN_WEEK = 60 * 60 * 24 * 7


class BaseService:
    """Base class for Gmail Service."""

    def __init__(
            self,
            api_manager: GoogleGmailApiManager,
            logger=None,
            **_
    ):
        self.api_manager = api_manager
        self.logger = logger


class LabelsService(BaseService):
    """Labels Service."""
    def __init__(self, user_email: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_email = user_email

    async def list_labels(self):
        """List labels for a given user_email."""
        label_jsons = await self.api_manager.list_labels(user_email=self.user_email)
        return [GmailLabel(**label_json) for label_json in label_jsons]

    async def create_label(self, label: str):
        """Creates a new label."""
        label_json = await self.api_manager.create_label(
            user_email=self.user_email,
            label_name=label
        )
        return GmailLabel(**label_json)


class MessagesService(BaseService):
    """Messages Service."""

    def __init__(self, user_email: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_email = user_email

    @staticmethod
    def build_messages_filter(
            after_ts: int | None = None,
            before_ts: int | None = None,
            labels: list[str] | None = None,
            subject_filter: str | None = None,
            sender_filter: str | list[str] | None = None,
            recipient_filter: str | None = None,
            mailbox_read_status: MailboxReadEnum = MailboxReadEnum.BOTH
    ) -> str:
        """Build Messages filter string.

        Args:
            after_ts: Timestamp in seconds to fetch emails after
            before_ts: Timestamp in seconds to fetch emails before
            labels: List of labels to filter with
            subject_filter: Subject to search for emails with
            sender_filter: Sender to search for emails with
            recipient_filter: Recipient to search for emails with
            mailbox_read_status: Whether to fetch only read, unread or both

        Returns:
            str: Messages filter string
        """
        filters = []
        if after_ts:
            filters.append(f"after:{after_ts}")

        if before_ts:
            filters.append(f"before:{before_ts}")

        if subject_filter:
            filters.append(f"subject:{subject_filter}")

        if sender_filter:
            if not isinstance(sender_filter, list):
                sender_filter = [sender_filter]

            sender_filter_ = " OR ".join(
                f"from:{sender}" for sender in sender_filter
            )
            filters.append(f"({sender_filter_})")

        if recipient_filter:
            filters.append(f"to:{recipient_filter}")

        if labels and any(label for label in labels):
            labels_include_filter = " OR ".join(
                f"label:{label}" for label in labels
                if label and not label.startswith("-")
            )
            labels_exclude_filter = " AND ".join(
                f"-label:{label[1:]}" for label in labels
                if label and label.startswith("-")
            )
            filters.append(
                " AND ".join(
                    label for label in (labels_include_filter, labels_exclude_filter)
                    if label
                )
            )

        if mailbox_read_status == MailboxReadEnum.UNREAD:
            filters.append("is:unread")
        elif mailbox_read_status == MailboxReadEnum.READ:
            filters.append("is:read")

        return " AND ".join(filters)

    async def list_messages(
            self,
            after_ts: int,
            limit: int,
            labels: list[str] | None = None,
            skip_ids: set[str] | None = None,
            mailbox_read_status: MailboxReadEnum = MailboxReadEnum.BOTH
    ) -> list[GmailMessage]:
        """List messages for a given user_email.

        Args:
            after_ts: Timestamp in seconds to fetch emails after
            labels: List of folders (labels) to filter with
            limit: Number of messages to fetch
            skip_ids: Message IDs to skip
            mailbox_read_status: Whether to fetch only read, unread or both

        Returns:
            list[GmailMessage]: List of messages
        """

        # Since the sorting of the messages is DESC we would be fetching messages
        # in intervals and fetch additional ones if needed
        before_ts = after_ts + SECONDS_IN_WEEK
        skip_ids = skip_ids or set()
        message_ids = []

        while (
            (after_ts < unix_now() // NUM_OF_MILLI_IN_SEC)
            and len(message_ids) < limit
        ):
            new_message_ids = await self.search_messages(
                after_ts=after_ts,
                before_ts=before_ts,
                labels=labels,
                mailbox_read_status=mailbox_read_status
            )
            message_ids.extend(
                message_id for message_id in new_message_ids[::-1]
                if message_id not in skip_ids
            )
            after_ts, before_ts = before_ts, before_ts + SECONDS_IN_WEEK

        messages_coros = [
            self.get_message_by_id(message_id) for message_id in message_ids[:limit]
        ]
        return sorted(
            await asyncio.gather(*messages_coros),
            key=lambda m: m.internal_date
        )

    async def search_messages(
            self,
            after_ts: int | None,
            before_ts: int | None = None,
            subject_filter: str | None = None,
            sender_filter: str | list[str] | None = None,
            recipient_filter: str | None = None,
            labels: list[str] | None = None,
            limit: int | None = None,
            mailbox_read_status: MailboxReadEnum = MailboxReadEnum.BOTH
    ) -> list[str]:
        """List messages for a given user_email.

        Args:
            after_ts: Timestamp in seconds to fetch emails after
            before_ts: Timestamp in seconds to fetch emails before
            labels: List of folders (labels) to filter with
            limit: Maximum number of message IDs to return
            subject_filter: Subject to search for emails with
            recipient_filter: Recipient to search for emails with
            sender_filter: Sender to search for emails with
            mailbox_read_status: Whether to fetch only read, unread or both

        Returns:
            list[str]: List of messages IDs
        """
        query = self.build_messages_filter(
            after_ts=after_ts,
            before_ts=before_ts,
            labels=labels,
            subject_filter=subject_filter,
            sender_filter=sender_filter,
            recipient_filter=recipient_filter,
            mailbox_read_status=mailbox_read_status,
        )

        return await self.api_manager.list_messages(
            user_email=self.user_email,
            max_results=limit,
            query=query,
        )

    async def search_by_message_id(self, message_id: str) -> list[str]:
        """Get message by rfc822 Message-Id header."""
        query = f"rfc822msgid:{message_id}"
        message_ids = await self.api_manager.list_messages(
            user_email=self.user_email,
            query=query
        )
        return message_ids

    async def get_message_by_id(
            self,
            message_id: str,
            format_: str = "full",
            metadata_headers: list[str] | None = None
    ) -> GmailMessage:
        """Get message by internal Gmail ID."""
        message_json = await self.api_manager.get_message(
            self.user_email,
            message_id,
            format_=format_,
            metadata_headers=metadata_headers,
        )
        return GmailMessage(**message_json)

    async def get_thread_by_id(
            self,
            thread_id: str,
            format_: str = "full",
            metadata_headers: list[str] | None = None
    ) -> GmailThread:
        """Get message thread by internal Gmail ID."""
        thread_json = await self.api_manager.get_thread(
            self.user_email,
            thread_id,
            format_=format_,
            metadata_headers=metadata_headers,
        )
        return GmailThread(**thread_json)

    async def delete_message(self, message_id: str) -> str:
        """Delete message from Gmail."""
        await self.api_manager.delete_message(
            self.user_email,
            message_id=message_id
        )
        return message_id

    async def trash_message(self, message_id: str) -> str:
        """Delete message from Gmail."""
        await self.api_manager.trash_message(
            self.user_email,
            message_id=message_id
        )
        return message_id

    async def set_message_mime_content(self, message: GmailMessage) -> None:
        """Set message's MIME content.'"""
        message_payload = await self.api_manager.get_message(
            user_email=self.user_email,
            message_id=message.id,
            format_="raw"
        )
        message.mime_content = message_payload["raw"]

    async def enrich_attachments(
            self,
            message_id: str,
            message_part: GmailMessagePart
    ) -> None:
        """Fetch attachments data for a message."""
        if message_part.is_attachment():
            attachment_body = await self.api_manager.get_attachment(
                self.user_email,
                message_id=message_id,
                attachment_id=message_part.body.attachment_id
            )
            message_part.body.data = attachment_body["data"]

        message_part_coros = [
            self.enrich_attachments(message_id, message_part_embedded)
            for message_part_embedded in (message_part.parts or [])
        ]
        await asyncio.gather(*message_part_coros)

    async def add_labels(self, message_ids: list[str], label_ids: list[str]) -> None:
        """Add labels to messages."""
        await self.api_manager.batch_modify(
            self.user_email,
            message_ids=message_ids,
            add_label_ids=label_ids,
        )

    async def remove_labels(self, message_ids: list[str], label_ids: list[str]) -> None:
        """Remove labels from messages."""
        await self.api_manager.batch_modify(
            self.user_email,
            message_ids=message_ids,
            remove_label_ids=label_ids,
        )

    async def mark_messages_as_read(
            self,
            message_ids: list[str]
    ) -> None:
        """Mark messages as read."""
        if not message_ids:
            return

        await self.api_manager.batch_modify(
            self.user_email,
            message_ids=message_ids,
            remove_label_ids=["UNREAD"]
        )

    async def reply_to_message(
            self,
            message: GmailMessage,
            to: list[str],
            body: str,
            attachments_paths: list[str] = None
    ):
        """Reply to an email with the specified arguments.

        Args:
            message (GmailMessage): Original message to reply
            to (list[str]): List of email addressed to send email to
            body (str): Email body
            attachments_paths (list[str]): List of attachment paths to send with email

        Returns:
            Message details JSON data
        """
        reply = MIMEMultipart()
        reply["From"] = self.user_email
        reply["To"] = ",".join(to)
        reply["Subject"] = f"Re: {message.payload.subject}"
        reply["In-Reply-To"] = message.payload.message_id
        reply["References"] = (
            message.payload.message_id if not
            message.payload.get_field_from_headers("references") else (
                message.payload.message_id + " " +
                message.payload.get_field_from_headers("references")
            )
        )

        set_body(reply, body)
        set_attachments(reply, attachments_paths)

        for file_attachment in message.payload.file_attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(file_attachment.body.body_decoded)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename=\"{file_attachment.filename}\""
            )
            reply.attach(part)

        message_json = await self.api_manager.send_email(
            sender=self.user_email,
            message=reply,
        )
        return GmailMessage(**message_json)

    async def forward_message(
            self,
            message: GmailMessage,
            to: list[str],
            cc: list[str],
            bcc: list[str],
            subject: str,
            body: str,
            attachments_paths: list[str] = None
    ):
        """Forward an email with the specified arguments.

        Args:
            message (GmailMessage): Original message to forward
            to (list[str]): List of email addressed to send email to
            cc (list[str]): List of email addressed to use for email CC
            bcc (list[str]): List of email addressed to use for email BCC
            subject (str): Email subject
            body (str): Email body
            attachments_paths (list[str]): List of attachment paths to send with email

        Returns:
            Message details JSON data
        """
        forward = MIMEMultipart()
        forward["From"] = self.user_email
        forward["To"] = ",".join(to)
        forward["Subject"] = subject
        forward["In-Reply-To"] = message.payload.message_id
        forward["References"] = (
            message.payload.message_id if not
            message.payload.get_field_from_headers("references") else (
                    message.payload.message_id + " " +
                    message.payload.get_field_from_headers("references")
            )
        )
        if cc:
            forward["CC"] = ",".join(cc)
        if bcc:
            forward["BCC"] = ",".join(bcc)

        original_body = get_payload_decoded(
            BytesParser().parsebytes(message.mime_content)
        )
        set_body(
            forward,
            body + FORWARD_EMAIL_TEMPLATE.format(
                from_=message.payload.from_,
                date=message.payload.get_field_from_headers("date"),
                subject=message.payload.subject,
                to=message.payload.get_field_from_headers("to"),
                content=original_body
            )
        )
        set_attachments(forward, attachments_paths)

        for file_attachment in message.payload.file_attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(file_attachment.body.body_decoded)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename=\"{file_attachment.filename}\""
            )
            forward.attach(part)

        message_json = await self.api_manager.send_email(
            sender=self.user_email,
            message=forward,
        )
        return GmailMessage(**message_json)

    async def send_email(
            self,
            to: list[str],
            subject: str,
            body: str,
            cc: list[str] = None,
            bcc: list[str] = None,
            reply_to: list[str] = None,
            attachments_paths: list[str] = None
    ) -> GmailMessage:
        """Send email with the specified arguments.

        Args:
            to (list[str]): List of email addressed to send email to
            cc (list[str]): List of email addressed to use for email CC
            bcc (list[str]): List of email addressed to use for email BCC
            reply_to(list[str]): List of email addressed to use for reply to
            subject (str): Email subject
            body (str): Email body
            attachments_paths (list[str]): List of attachment paths to send with email

        Returns:
            Message details JSON data
        """
        message = MIMEMultipart()
        message["From"] = self.user_email
        message["To"] = ",".join(to)
        message["Subject"] = subject

        if cc:
            message["CC"] = ",".join(cc)
        if bcc:
            message["BCC"] = ",".join(bcc)
        if reply_to:
            message["Reply-To"] = ",".join(reply_to)

        set_body(message, body)
        set_attachments(message, attachments_paths)

        message_json = await self.api_manager.send_email(
            sender=self.user_email,
            message=message,
        )
        return GmailMessage(**message_json)

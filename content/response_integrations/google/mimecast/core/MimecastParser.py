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
import codecs
from ..core.datamodels import *
from typing import Iterable, Any
import re

from TIPCommon.types import SingleJson


class MimecastParser:
    def build_base_model(self, raw_data):

        items = raw_data.get("data")[0].get("items")

        return [BaseModel(raw_data=item) for item in items]

    def build_list_of_base_objects(self, raw_data):
        return [BaseModel(raw_data=item) for item in raw_data]

    def build_messages_list(self, raw_data):
        data = raw_data.get("data", [])
        emails_data = data[0].get("trackedEmails", []) if data else []
        return [self.build_message_object(item) for item in emails_data]

    def build_list_of_hold_messages(self, raw_data):
        data = raw_data.get("data", [])
        return [self.build_hold_message_objects(item) for item in data]

    def build_hold_message_objects(self, raw_data):
        return HoldMessage(
            raw_data=raw_data,
            message_id=raw_data.get("id"),
            subject=raw_data.get("subject"),
            sender=raw_data.get("from", {}).get("emailAddress"),
            to=raw_data.get("to", {}).get("emailAddress"),
        )

    def build_message_object(self, raw_data):
        return Message(
            raw_data=raw_data,
            tracking_id=raw_data.get("id"),
            status=raw_data.get("status"),
            received=raw_data.get("received"),
            route=raw_data.get("route"),
            info=raw_data.get("info"),
            subject=raw_data.get("subject"),
            sender=raw_data.get("fromEnv", {}).get("emailAddress"),
            to=raw_data.get("to", [{}])[0].get("emailAddress"),
        )

    def build_message_details_object(self, raw_data):
        data = raw_data.get("data", [])
        message_data = data[0] if data else {}
        return MessageDetails(
            raw_data=message_data,
            tracking_id=message_data.get("id"),
            message_id=self.__parse_message_id(payload=message_data),
            reason=self.__traverse_json_path_safe(
                payload=message_data, path=("queueInfo", "reason"), result_default=""
            ),
            risk=self.__traverse_json_path_safe(
                payload=message_data,
                path=("spamInfo", "spamProcessingDetail", "verdict", "risk"),
                result_default="",
            ),
            queue_detail_status=self.__traverse_json_path_safe(
                payload=message_data,
                path=("recipientInfo", "txInfo", "queueDetailStatus"),
                result_default="",
            ),
            transmission_components=self.__traverse_json_path_safe(
                payload=message_data,
                path=("recipientInfo", "txInfo", "transmissionComponents"),
                result_default=[],
            ),
            components=self.__traverse_json_path_safe(
                payload=message_data,
                path=("recipientInfo", "recipientMetaInfo", "components"),
                result_default=[],
            ),
            sent=self.__traverse_json_path_safe(
                payload=message_data,
                path=("recipientInfo", "messageInfo", "sent"),
                result_default=[],
            ),
        )

    # Recursively traverse through payload by specified key path, without breaking if some key isn't there
    @staticmethod
    def __traverse_json_path_safe(
        payload: dict, path: Iterable[str], result_default: Any
    ) -> Any:
        result = payload
        for key in path:
            result = result.get(key, {})
        return result or result_default

    # Parse internal message_id for the email from the transmissionInfo
    # As a fallback use id from the queueInfo
    def __parse_message_id(
        self,
        payload: dict,
        path: Iterable[str] = ("recipientInfo", "messageInfo", "transmissionInfo"),
    ) -> Any:
        transmission_info = self.__traverse_json_path_safe(
            payload, path, result_default=None
        )

        if transmission_info is not None:
            message_id_match = re.search(
                r"(?i)message-id: &lt;(.+)&gt;", transmission_info
            )
            if message_id_match is not None:
                return message_id_match.group(1)

        return self.__traverse_json_path_safe(
            payload, ("queueInfo", "id"), result_default=None
        )

    def build_block_sender_policy(self, raw_data: SingleJson) -> BlockSenderPolicy:
        return BlockSenderPolicy.from_json(block_sender_policy_json=raw_data)

    def build_attachment_object(self, raw_data: SingleJson) -> Attachment:
        return Attachment.from_json(attachment_json=raw_data)

    def build_list_of_attachments(self, raw_data: SingleJson) -> list[Attachment]:
        data = raw_data.get("data", [])
        attachments = data[0].get("attachments", [])

        return [self.build_attachment_object(item) for item in attachments]

    def parse_url_for_attachment(self, raw_data: SingleJson) -> str:
        url = raw_data.get("data", [{}])[0].get("urls")[0]
        cleaned_url = codecs.decode(url, "unicode_escape") if r"\u" in url else url

        return cleaned_url

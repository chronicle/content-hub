# Copyright 2025 Google LLC
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

import base64
import datetime
import re

from ...consts import NUM_OF_MILLI_IN_SEC
from .data_models import *


class PubSubParser:
    """Parser class for Google PubSub API responses"""

    @staticmethod
    def _get_resource_name(resource_id):
        """Get simplified resource name

        Args:
            resource_id (str): full GCP resource identifier

        Returns:
            str: simplified resource name

        """
        return resource_id.split("/")[-1] if resource_id.find("/") != -1 else resource_id

    @classmethod
    def build_topic_object(cls, raw_data):
        """Builds `Topic` object from api response
        Args:
            raw_data (dict): http response json content

        Returns:
            Topic: parsed response object

        """
        schema_settings = (
            cls.build_schema_settings_object(raw_data.get("schemaSettings"))
            if raw_data.get("schemaSettings")
            else None
        )
        return Topic(
            raw_data=raw_data,
            name=cls._get_resource_name(raw_data.get("name", "")),
            identifier=raw_data.get("name", ""),
            labels=raw_data.get("labels", {}),
            schema_settings=schema_settings,
            message_retention_duration=raw_data.get("messageRetentionDuration"),
        )

    @staticmethod
    def build_schema_settings_object(raw_data):
        """Builds `SchemaSettings` object from api response
        Args:
            raw_data (dict): http response json content

        Returns:
            SchemaSettings: parsed response object

        """
        return SchemaSettings(
            raw_data=raw_data,
            schema=raw_data.get("schema"),
            encoding=raw_data.get("encoding"),
            first_revision_id=raw_data.get("firstRevisionId"),
            last_revision_id=raw_data.get("lastRevisionId"),
        )

    @classmethod
    def build_subscription_object(cls, raw_data):
        """Builds `Subscription` object from api response
        Args:
            raw_data (dict): http response json content

        Returns:
            Subscription: parsed response object

        """
        retention = raw_data.get("topicMessageRetentionDuration")
        retention_duration = re.match(r"(\d+)s", retention or "")
        if retention_duration is not None:
            retention = int(retention_duration.group(1))

        return Subscription(
            raw_data=raw_data,
            name=cls._get_resource_name(raw_data.get("name", "")),
            identifier=raw_data.get("name"),
            topic_identifier=raw_data.get("topic"),
            ack_deadline_secs=int(raw_data.get("ackDeadlineSeconds")),
            retain_ack_messages=raw_data.get("retainAckedMessages"),
            message_retention_duration=raw_data.get("messageRetentionDuration"),
            labels=raw_data.get("labels"),
            message_ordering=raw_data.get("enableMessageOrdering"),
            query_filter=raw_data.get("filter"),
            topic_message_retention_duration=retention,
            state=raw_data.get("state"),
        )

    @staticmethod
    def build_pub_sub_message_object(raw_data, encoding="utf-8"):
        """Builds `PubSubMessage` object from api response
        Args:
            raw_data (dict): http response json content
            encoding (str): pubsub message encoding. defaults to 'utf-8'

        Returns:
            PubSubMessage: parsed response object

        """
        publish_time_timestamp = int(
            datetime.datetime.fromisoformat(raw_data.get("publishTime")).timestamp()
            * NUM_OF_MILLI_IN_SEC
        )
        return PubSubMessage(
            raw_data=raw_data,
            data=base64.b64decode(raw_data.get("data")).decode(encoding),
            attributes=raw_data.get("attributes"),
            message_id=raw_data.get("messageId"),
            publish_time=publish_time_timestamp,
            ordering_key=raw_data.get("orderingKey"),
        )

    @classmethod
    def build_received_message_object(cls, raw_data, encoding="utf-8"):
        """Builds `ReceivedMessage` object from api response
        Args:
            raw_data (dict): http response json content
            encoding (str): pubsub message encoding. defaults to 'utf-8'

        Returns:
            ReceivedMessage: parsed response object

        """
        message = (
            cls.build_pub_sub_message_object(raw_data.get("message"), encoding)
            if raw_data.get("message")
            else None
        )
        return ReceivedMessage(
            raw_data=raw_data,
            ack_id=raw_data.get("ackId"),
            message=message,
            delivery_attempt=raw_data.get("deliveryAttempt"),
        )

    @classmethod
    def build_received_messages_list(cls, raw_data, encoding="utf-8"):
        """Builds list of `ReceivedMessage` objects from api response
        Args:
            raw_data (dict): http response json content
            encoding (str): pubsub message encoding. defaults to 'utf-8'

        Returns:
            list[ReceivedMessage]: list of parsed response objects

        """
        return [
            cls.build_received_message_object(msg, encoding)
            for msg in raw_data.get("receivedMessages", [])
        ]

    @staticmethod
    def build_message_ids_list(raw_data):
        """Builds list of message ids from api response
        Args:
            raw_data (dict): http response json content

        Returns:
            list[str]: list of message ids

        """
        return raw_data.get("messageIds", [])

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

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class SchemaSettings:
    raw_data: dict
    schema: str
    encoding: str = None
    first_revision_id: str = None
    last_revision_id: str = None

    def json(self):
        return self.raw_data


@dataclasses.dataclass(frozen=True)
class Topic:
    raw_data: dict
    name: str
    identifier: str
    labels: dict = None
    schema_settings: SchemaSettings = None
    message_retention_duration: int = None

    def json(self):
        return self.raw_data


@dataclasses.dataclass(frozen=True)
class Subscription:
    raw_data: dict
    name: str
    identifier: str
    topic_identifier: str
    state: str
    ack_deadline_secs: int = None
    retain_ack_messages: bool = None
    message_retention_duration: int = None
    labels: dict = None
    message_ordering: bool = None
    query_filter: str = None
    topic_message_retention_duration: int = None

    def json(self):
        return self.raw_data


@dataclasses.dataclass(frozen=False)
class PubSubMessage:
    raw_data: dict
    data: str = None
    attributes: dict = None
    message_id: str = None
    publish_time: int = None
    ordering_key: str = None

    def json(self):
        return self.raw_data


@dataclasses.dataclass(frozen=True)
class ReceivedMessage:
    raw_data: dict
    ack_id: str
    message: PubSubMessage
    delivery_attempt: int

    def json(self):
        return self.raw_data

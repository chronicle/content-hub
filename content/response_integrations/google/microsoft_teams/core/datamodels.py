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

from typing import Any, Iterable

from TIPCommon.transformation import add_prefix_to_dict, dict_to_flat


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Message(BaseModel):
    def __init__(self, raw_data, message_id, created_date, sender):
        super(Message, self).__init__(raw_data)
        self.message_id = message_id
        self.created_date = created_date
        self.sender = sender


class Me(BaseModel):
    def __init__(self, raw_data, display_name, email, user_id):
        super(Me, self).__init__(raw_data)
        self.display_name = display_name
        self.email = email
        self.user_id = user_id


class Chat(BaseModel):
    def __init__(
            self, raw_data, topic=None, chat_id=None, chat_type=None, members=None
    ):
        super(Chat, self).__init__(raw_data)
        self.topic = topic
        self.chat_id = chat_id
        self.chat_type = chat_type
        self.members = ",".join(members) if members else "N/A"

    def to_table(self):
        return {
            "ID": self.chat_id,
            "Type": self.chat_type,
            "Topic": self.topic,
            "Members": self.members,
        }


class Channel(BaseModel):
    def __init__(self, raw_data):
        super(Channel, self).__init__(raw_data)


class User(BaseModel):
    def __init__(self, raw_data, user_id, display_name, email):
        super(User, self).__init__(raw_data)
        self.user_id = user_id
        self.display_name = display_name
        self.email = email


class Reply(BaseModel):
    def __init__(self, raw_data: dict[str, Any]) -> None:
        super(Reply, self).__init__(raw_data)


class UserCollection(BaseModel):
    def __init__(self, users_iterable: Iterable[dict]) -> None:
        users_list = list(users_iterable)
        super().__init__(users_list)

    def to_dict(self) -> dict:
        """
        Converts the user collection to a mapping of displayName/mail to user id.
        """
        mapping = {}
        for item in self.raw_data:
            if item.get("displayName"):
                mapping[item.get("displayName")] = item.get("id")
            if item.get("mail"):
                mapping[item.get("mail").casefold()] = item.get("id")
        return mapping

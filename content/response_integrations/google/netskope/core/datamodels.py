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
from typing import Any


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Client(BaseModel):
    def __init__(self, raw_data, device_id, os, users):
        super(Client, self).__init__(raw_data)
        self.device_id = device_id
        self.os = os
        self.users = users

    def to_table_data(self):
        return {"Device ID": self.device_id, "OS ": self.os, "Users": self.users}


class User(BaseModel):
    def __init__(self, raw_data, username):
        super(User, self).__init__(raw_data)
        self.username = username


class AddEntitiesResult(BaseModel):
    def __init__(
        self,
        added_entities: list[str],
        failed_entities: list[str],
        url_list_name: str,
        modify_by: str,
        modify_time: str,
        pending: int,
    ):
        super().__init__({})
        self.added_entities = added_entities
        self.failed_entities = failed_entities
        self.url_list_name = url_list_name
        self.modify_by = modify_by
        self.modify_time = modify_time
        self.pending = pending

    def to_json(self) -> dict[str, Any]:
        return {
            "added_entities": self.added_entities,
            "failed_entities": self.failed_entities,
            "url_list_name": self.url_list_name,
            "modify_by": self.modify_by,
            "modify_time": self.modify_time,
            "pending": self.pending,
        }

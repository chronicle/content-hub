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
from .datamodels import User, Group, Policy


class AWSIAMParser:
    @staticmethod
    def build_users_obj(objects_data):
        return [User.from_json(user_json=user) for user in objects_data]

    @staticmethod
    def build_user_obj(objects_data):
        return User.from_json(user_json=objects_data.get("User"))

    @staticmethod
    def build_groups_obj(objects_data):
        return [
            Group.from_json(group_json=group) for group in objects_data
        ]

    @staticmethod
    def build_group_obj(objects_data):
        return Group.from_json(group_json=objects_data.get("Group"))

    @staticmethod
    def build_policy_obj(raw_data):
        return Policy.from_json(policy_json=raw_data)

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
from .datamodels import User, Channel, Message


class SlackTransformationLayer:
    """
    Slack Transformation Layer.
    Class for object building from raw_data with static methods build_siemplify_{object}_obj.
    """

    @staticmethod
    def build_siemplify_user_obj(user_data):
        return User(raw_data=user_data, **user_data)

    @staticmethod
    def build_siemplify_channel_obj(channel_data):
        return Channel(raw_data=channel_data, **channel_data)

    @staticmethod
    def build_siemplify_message_obj(message_data):
        return Message(raw_data=message_data, **message_data)

    @staticmethod
    def build_siemplify_message_obj_from_new_message(message_data):
        return Message(raw_data=message_data, **(message_data.get("message", {})))

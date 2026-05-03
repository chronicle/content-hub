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
from .datamodels import Client, User


class NetskopeTransformationalLayer:

    def build_siemplify_client(self, client_json):
        return Client(
            raw_data=client_json.get("attributes"),
            device_id=client_json.get("attributes", {}).get("_id"),
            os=client_json.get("attributes", {}).get("host_info", {}).get("os"),
            users=[
                self.build_siemplify_users(users_json).username
                for users_json in client_json.get("attributes", {}).get("users", [])
            ],
        )

    def build_siemplify_users(self, users_json):
        return User(raw_data=users_json, username=users_json.get("username"))

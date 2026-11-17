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
import dataclasses
from TIPCommon.transformation import dict_to_flat


class DslSearchResult:
    def __init__(self, raw_data, alert_id):
        self.raw_data = raw_data
        self.alert_id = alert_id

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.raw_data)


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    server: str
    username: str
    password: str
    jwt_token: str
    authenticate: bool
    verify_ssl: bool
    ca_certificate_file: str

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
from .datamodels import *


class McAfeeMvisionEDRV2Parser:
    def get_auth_token(self, raw_json):
        return f'{raw_json.get("token_type", "")} {raw_json.get("access_token", "")}'

    def build_siemplify_investigation(self, investigation_json):
        return Investigation(
            raw_data=investigation_json,
            name=investigation_json.get("attributes", {}).get("name"),
            owner=investigation_json.get("attributes", {}).get("owner"),
            created=investigation_json.get("attributes", {}).get("created"),
            investigation_id=investigation_json.get("id"),
            summary=investigation_json.get("attributes", {}).get("summary"),
            last_modified=investigation_json.get("attributes", {}).get("lastModified"),
            is_automatic=investigation_json.get("attributes", {}).get("isAutomatic"),
            hint=investigation_json.get("attributes", {}).get("hint"),
            case_type=investigation_json.get("attributes", {}).get("caseType"),
            investigated=investigation_json.get("attributes", {}).get("investigated"),
            status=investigation_json.get("attributes", {}).get("status"),
            priority=investigation_json.get("attributes", {}).get("priority"),
        )

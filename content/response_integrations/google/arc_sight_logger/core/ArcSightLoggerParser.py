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


class ArcSightLoggerParser:
    def get_auth_token(self, raw_json):
        return raw_json.get("log.loginResponse", "").get("log.return")

    def build_query_status_object(self, result_json):
        return QueryStatus(
            result_json,
            status=result_json.get("status"),
            result_type=result_json.get("result_type"),
            hit=result_json.get("hit"),
            scanned=result_json.get("scanned"),
            elapsed=result_json.get("elapsed"),
            message=result_json.get("message"),
        )

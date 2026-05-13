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


class F5BIGIPAccessPolicyManagerParser:

    @staticmethod
    def build_active_sessions_object(raw_data):
        active_session_data = raw_data.get("entries", {})

        return [
            ActiveSessionObject(
                raw_data=raw_data,
                active_session_id=active_session_key.split("/")[-1],
                stats=active_session_value.get("nestedStats"),
                client_ip=active_session_value.get("nestedStats", {})
                .get("entries", {})
                .get("clientIp", {})
                .get("description"),
                logon_user=active_session_value.get("nestedStats", {})
                .get("entries", {})
                .get("logonUser", {})
                .get("description"),
            )
            for active_session_key, active_session_value in active_session_data.items()
        ]

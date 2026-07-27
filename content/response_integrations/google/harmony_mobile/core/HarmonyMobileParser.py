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


class HarmonyMobileParser:

    @staticmethod
    def get_token(raw_data):
        return raw_data.get("data", {}).get("token")

    @staticmethod
    def build_alert_object(raw_data):
        return Alert(
            raw_data=raw_data,
            id=raw_data.get("id"),
            details=raw_data.get("details"),
            severity=raw_data.get("severity"),
            threat_factors=raw_data.get("threat_factors"),
            timestamp=raw_data.get("backend_last_updated"),
        )

    @staticmethod
    def build_device_object(raw_data):
        return Device(
            raw_data=raw_data,
            client_version=raw_data.get("client_version"),
            device_type=raw_data.get("device_type"),
            email=raw_data.get("email"),
            last_connection=raw_data.get("last_connection"),
            model=raw_data.get("model"),
            name=raw_data.get("name"),
            number=raw_data.get("number"),
            os_type=raw_data.get("os_type"),
            os_version=raw_data.get("os_version"),
            risk=raw_data.get("risk"),
            status=raw_data.get("status"),
        )

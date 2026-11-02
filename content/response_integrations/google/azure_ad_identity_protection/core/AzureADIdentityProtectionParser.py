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
from azure_ad_identity_protection.core.datamodels import *


class AzureADIdentityProtectionParser:
    def build_risk_detections_list(self, raw_data):
        return [self.build_risk_detection(item) for item in raw_data.get("value", [])]

    def build_risk_detection(self, raw_data):
        return RiskDetection(
            raw_data=raw_data,
            id=raw_data.get("id"),
            risk_event_type=raw_data.get("riskEventType"),
            risk_level=raw_data.get("riskLevel"),
            detected_date_time=raw_data.get("detectedDateTime"),
        )

    def build_user_object(self, raw_data):
        raw_data = raw_data[0] if raw_data else {}
        if raw_data:
            return User(
                raw_data=raw_data,
                id=raw_data.get("id"),
                is_deleted=raw_data.get("isDeleted"),
                is_processing=raw_data.get("isProcessing"),
                risk_level=raw_data.get("riskLevel"),
                risk_state=raw_data.get("riskState"),
                risk_detail=raw_data.get("riskDetail"),
                risk_updated=raw_data.get("riskLastUpdatedDateTime"),
                display_name=raw_data.get("userDisplayName"),
                principal_name=raw_data.get("userPrincipalName"),
            )

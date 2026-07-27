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


class Office365ManagementAPIParser:
    def get_auth_token(self, raw_json):
        return raw_json.get("access_token")

    def get_data_blobs(self, raw_data):
        return [DataBlob(item, item.get("contentUri")) for item in raw_data]

    def build_alerts(self, raw_data, mask_findings):
        return [self.build_alert(item, mask_findings) for item in raw_data]

    def build_alert(self, data, mask_findings):
        return Alert(
            raw_data=data,
            id=data.get("Id"),
            workload=data.get("Workload"),
            operation=data.get("Operation"),
            policy_names=[
                policy_detail.get("PolicyName")
                for policy_detail in data.get("PolicyDetails")
            ],
            incident_id=data.get("IncidentId"),
            creation_time=data.get("CreationTime"),
            policy_details=data.get("PolicyDetails"),
            mask_findings=mask_findings,
        )

    def build_audit_general_alerts(self, raw_data):
        return [self.build_audit_general_alert(item) for item in raw_data]

    @staticmethod
    def build_audit_general_alert(data):
        return AuditGeneralAlert(
            raw_data=data,
            id=data.get("Id"),
            workload=data.get("Workload"),
            operation=data.get("Operation"),
            incident_id=data.get("IncidentId"),
            creation_time=data.get("CreationTime"),
            severity=data.get("Severity"),
            status=data.get("Status"),
        )

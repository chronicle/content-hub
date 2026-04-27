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

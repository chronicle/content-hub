from __future__ import annotations

from .datamodels import (
    CVE,
    Alert,
    AlertComment,
    Asset,
    Framework,
    ScanStatus,
)


class OrcaSecurityParser:
    def build_results(
        self, raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    def build_alert_objects(self, raw_data):
        return [self.build_alert_object(item) for item in raw_data.get("data", [])]

    @staticmethod
    def build_alert_object(raw_data):
        alert_data = raw_data.get("data", {})
        asset_data = alert_data.get("AssetData", {}).get("value", {})
        return Alert(
            raw_data=raw_data,
            alert_id=alert_data.get("AlertId", {}).get("value"),
            title=alert_data.get("Title", {}).get("value"),
            details=alert_data.get("Details", {}).get("value"),
            severity=alert_data.get("Severity", {}).get("value"),
            created_at=alert_data.get("CreatedAt", {}).get("value"),
            asset_name=asset_data.get("asset_name"),
            asset_type=asset_data.get("asset_type"),
            type_string=alert_data.get("AlertType", {}).get("value"),
        )

    @staticmethod
    def build_alert_comment_object(raw_data):
        return AlertComment(raw_data=raw_data)

    def build_framework_objects(self, raw_data):
        return [
            self.build_framework_object(item)
            for item in raw_data.get("data", {}).get("frameworks", [])
        ]

    @staticmethod
    def build_framework_object(raw_data):
        return Framework(
            raw_data=raw_data,
            display_name=raw_data.get("display_name"),
            description=raw_data.get("description"),
            avg_score_percent=raw_data.get("avg_score_percent"),
            test_results_fail=raw_data.get("test_results", {}).get("FAIL"),
            test_results_pass=raw_data.get("test_results", {}).get("PASS"),
            active=raw_data.get("active"),
        )

    @staticmethod
    def build_scan_status_object(raw_data):
        return ScanStatus(
            raw_data=raw_data,
            scan_id=raw_data.get("scan_unique_id"),
            status=raw_data.get("status"),
        )

    @staticmethod
    def build_cve_object(raw_json):

        inventory = raw_json.get("Inventory") or {}
        installed_package = raw_json.get("InstalledPackage") or {}

        return CVE(
            raw_json,
            cve_id=raw_json.get("CveId"),
            summary=raw_json.get("Description"),
            fix_available=str(raw_json.get("PatchAvailable")).lower() == "yes",
            asset_name=inventory.get("Name"),
            published=raw_json.get("FirstSeen"),
            source_link=raw_json.get("SourceLink"),
            affected_packages=installed_package.get("Name"),
            severity=str(raw_json.get("CvssSeverity")).lower(),
        )

    @staticmethod
    def build_asset_object(raw_json):
        asset_data = raw_json.get("data") or {}
        return Asset(
            raw_json,
            asset_name=raw_json.get("name"),
            asset_type=raw_json.get("type"),
            asset_category=asset_data.get("Category", {}).get("value"),
            asset_subcategory=asset_data.get("SubCategory", {}).get("value"),
            asset_state=asset_data.get("State", {}).get("value"),
            state_severity=asset_data.get("RiskLevel", {}).get("value", "N/A"),
            state_created_at=asset_data.get("FirstSeen", {}).get("value", "N/A"),
            state_last_seen=raw_json.get("last_seen", "N/A"),
        )

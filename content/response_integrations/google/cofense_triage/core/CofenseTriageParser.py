from __future__ import annotations
from .datamodels import *
from typing import List


class CofenseTriageParser:

    @staticmethod
    def build_siemplify_url_object(raw_data):
        return URLObject(
            raw_data=raw_data,
            risk_score=(
                raw_data.get("data")[0].get("attributes", {}).get("risk_score")
                if raw_data.get("data")
                else None
            ),
            url=(
                raw_data.get("data")[0].get("attributes", {}).get("url")
                if raw_data.get("data")
                else None
            ),
            created_at=(
                raw_data.get("data")[0].get("attributes", {}).get("created_at")
                if raw_data.get("data")
                else None
            ),
            updated_at=(
                raw_data.get("data")[0].get("attributes", {}).get("updated_at")
                if raw_data.get("data")
                else None
            ),
            attributes=(
                raw_data.get("data")[0].get("attributes")
                if raw_data.get("data")
                else None
            ),
            url_type=(
                raw_data.get("data")[0].get("type") if raw_data.get("data") else None
            ),
            url_id=raw_data.get("data")[0].get("id") if raw_data.get("data") else None,
        )

    @staticmethod
    def build_siemplify_universal_object(raw_data):
        return UniversalObject(
            raw_data=raw_data,
            data_id=raw_data.get("data")[0].get("id") if raw_data.get("data") else None,
            data_type=(
                raw_data.get("data")[0].get("type") if raw_data.get("data") else None
            ),
            attributes=(
                raw_data.get("data")[0].get("attributes")
                if raw_data.get("data")
                else None
            ),
        )

    @staticmethod
    def build_siemplify_domain_details_object(raw_data):

        return DomainDetailsObject(
            raw_data=raw_data,
            data_id=raw_data.get("data")[0].get("id") if raw_data.get("data") else None,
            data_type=(
                raw_data.get("data")[0].get("type") if raw_data.get("data") else None
            ),
            attributes=(
                raw_data.get("data")[0].get("attributes")
                if raw_data.get("data")
                else None
            ),
            risk_score=(
                raw_data.get("data")[0].get("attributes", {}).get("risk_score")
                if raw_data.get("data")
                else None
            ),
            hostname=(
                raw_data.get("data")[0].get("attributes", {}).get("hostname")
                if raw_data.get("data")
                else None
            ),
        )

    @staticmethod
    def build_siemplify_report_reporters_object(raw_data):

        return ReportReportersObject(
            raw_data=raw_data,
            data_id=raw_data.get("data").get("id") if raw_data.get("data") else None,
            data_type=(
                raw_data.get("data").get("type") if raw_data.get("data") else None
            ),
            attributes=(
                raw_data.get("data").get("attributes") if raw_data.get("data") else None
            ),
            email=(
                raw_data.get("data").get("attributes", {}).get("email")
                if raw_data.get("data")
                else None
            ),
            reports_count=(
                raw_data.get("data").get("attributes", {}).get("reports_count")
                if raw_data.get("data")
                else None
            ),
            reputation_score=(
                raw_data.get("data").get("attributes", {}).get("reputation_score")
                if raw_data.get("data")
                else None
            ),
            vip=(
                raw_data.get("data").get("attributes", {}).get("vip")
                if raw_data.get("data")
                else None
            ),
        )

    @staticmethod
    def build_siemplify_report_headers_object(raw_data):
        related_objects_data = raw_data.get("data", [])
        return [
            ReportHeadersObject(
                raw_data=related_object_data,
                data_id=related_object_data.get("id"),
                data_type=related_object_data.get("type"),
                attributes=related_object_data.get("attributes"),
                key=related_object_data.get("attributes", {}).get("key"),
                value=related_object_data.get("attributes", {}).get("value"),
            )
            for related_object_data in related_objects_data
        ]

    @staticmethod
    def build_siemplify_ti_object(raw_data):
        return ThreaIndicatorDetailsObject(
            raw_data=raw_data,
            ti_id=raw_data.get("data")[0].get("id") if raw_data.get("data") else None,
            ti_type=(
                raw_data.get("data")[0].get("attributes", {}).get("threat_type")
                if raw_data.get("data")
                else None
            ),
            attributes=(
                raw_data.get("data")[0].get("attributes")
                if raw_data.get("data")
                else None
            ),
            ti_threat_source=(
                raw_data.get("data")[0].get("attributes", {}).get("threat_source")
                if raw_data.get("data")
                else None
            ),
            ti_threat_level=(
                raw_data.get("data")[0].get("attributes", {}).get("threat_level")
                if raw_data.get("data")
                else None
            ),
            ti_created_at=(
                raw_data.get("data")[0].get("attributes", {}).get("created_at")
                if raw_data.get("data")
                else None
            ),
            ti_updated_at=(
                raw_data.get("data")[0].get("attributes", {}).get("updated_at")
                if raw_data.get("data")
                else None
            ),
        )

    @staticmethod
    def build_siemplify_report_object(raw_data):
        return UniversalObject(
            raw_data=raw_data,
            data_id=raw_data.get("data").get("id") if raw_data.get("data") else None,
            data_type=(
                raw_data.get("data").get("type") if raw_data.get("data") else None
            ),
            attributes=(
                raw_data.get("data").get("attributes") if raw_data.get("data") else None
            ),
        )

    @staticmethod
    def build_siemplify_categories_object(raw_data):

        related_objects_data = raw_data.get("data", [])
        return [
            CategoriesObject(
                raw_data=related_object_data,
                category_id=related_object_data.get("id"),
                name=related_object_data.get("attributes", {}).get("name"),
                score=related_object_data.get("attributes", {}).get("score"),
                archived=related_object_data.get("attributes", {}).get("archived"),
                malicious=related_object_data.get("attributes", {}).get("malicious"),
            )
            for related_object_data in related_objects_data
        ]

    @staticmethod
    def build_siemplify_reports_object(raw_data):
        return ReportObject(
            raw_data=raw_data,
            tags=(
                raw_data.get("data").get("attributes", {}).get("tags")
                if raw_data.get("data")
                else None
            ),
        )

    def build_related_entities_objects(self, raw_data):
        return [
            self.build_siemplify_report_object(item)
            for item in raw_data.get("data", [])
        ]

    def build_threat_indicators_objects(self, raw_data):
        return [
            self.build_threat_indicators_object(item)
            for item in raw_data.get("data", [])
        ]

    def build_attachment_objects(self, raw_data):
        return [self.build_attachment_object(item) for item in raw_data.get("data", [])]

    def build_attachment_payload_objects(self, raw_data):
        return [
            self.build_attachment_payload_object(item)
            for item in raw_data.get("data", [])
        ]

    @staticmethod
    def build_threat_indicators_object(data):
        return ThreaIndicatorDetailsObject(
            raw_data=data,
            threat_type=data.get("attributes", {}).get("threat_type"),
            threat_value=data.get("attributes", {}).get("threat_value"),
        )

    @staticmethod
    def build_attachment_object(data):
        return Attachment(
            raw_data=data,
            id=data.get("id"),
            payload_id=data.get("relationships", {})
            .get("attachment_payload", {})
            .get("data", {})
            .get("id"),
            type=data.get("type"),
            attributes=data.get("attributes", {}),
            filename=data.get("attributes", {}).get("filename"),
            size=data.get("attributes", {}).get("size"),
            is_child=data.get("attributes", {}).get("is_child"),
            created_at=data.get("attributes", {}).get("created_at"),
            updated_at=data.get("attributes", {}).get("updated_at"),
        )

    @staticmethod
    def build_attachment_payload_object(data):
        return AttachmentPayload(
            raw_data=data,
            id=data.get("id"),
            mime_type=data.get("attributes", {}).get("mime_type"),
            md5=data.get("attributes", {}).get("md5"),
            sha256=data.get("attributes", {}).get("sha256"),
            risk_score=data.get("attributes", {}).get("risk_score"),
        )

    @staticmethod
    def get_alert(
        report,
        urls,
        hostnames,
        threat_indicators,
        attachments,
        attachments_payloads,
        comments,
        headers,
    ):
        return Alert(
            raw_data=report,
            id=report.get("id"),
            location=report.get("attributes", {}).get("location"),
            risk_score=report.get("attributes", {}).get("risk_score"),
            created_at=report.get("attributes", {}).get("created_at"),
            updated_at=report.get("attributes", {}).get("updated_at"),
            urls=urls,
            hostnames=hostnames,
            threat_indicators=threat_indicators,
            attachments=attachments,
            attachments_payloads=attachments_payloads,
            comments=comments,
            headers=headers,
        )

    @staticmethod
    def get_alert_ids(report):
        threat_ids = [threat_id.get("id") for threat_id in report.get("data", [])]

        return threat_ids

    @staticmethod
    def related_reports(threat_data):
        related_reports = [threat_id for threat_id in threat_data.get("data", [])]

        return related_reports

    @staticmethod
    def build_related_report_object(data):
        return RelatedReportObject(
            raw_data=data,
            id=data.get("id"),
            location=data.get("attributes", {}).get("location"),
            created_at=data.get("attributes", {}).get("created_at"),
            subject=data.get("attributes", {}).get("subject"),
        )

    def build_playbooks_list(self, raw_data: dict) -> List[Playbook]:
        return [self.build_playbook_object(item) for item in raw_data.get("data", [])]

    @staticmethod
    def build_playbook_object(raw_json: dict) -> Playbook:
        return Playbook(
            raw_data=raw_json,
            name=raw_json.get("attributes", {}).get("name"),
            active=raw_json.get("attributes", {}).get("active"),
            identifier=raw_json.get("id"),
            description=raw_json.get("attributes", {}).get("description"),
            tags=raw_json.get("attributes", {}).get("report_tags", [])
            + raw_json.get("attributes", {}).get("cluster_tags", []),
            created_at=raw_json.get("attributes", {}).get("created_at"),
        )

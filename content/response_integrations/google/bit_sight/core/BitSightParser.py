from __future__ import annotations
from bit_sight.core.datamodels import *
from bit_sight.core.utils import convert_list_to_comma_string
from TIPCommon import none_to_default_value


class BitSightParser:
    def build_results(
        self,
        raw_json,
        method,
        data_key="results",
        limit=None,
        pure_data=False,
        **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    @staticmethod
    def build_alert_object(raw_data):
        return Alert(
            raw_data=raw_data,
            alert_id=raw_data.get("guid"),
            trigger=raw_data.get("trigger"),
            severity=raw_data.get("severity"),
            alert_type=raw_data.get("alert_type"),
            alert_date=raw_data.get("alert_date"),
            company_id=raw_data.get("company_guid"),
            message=raw_data.get("details", {}).get("message"),
        )

    @staticmethod
    def build_finding_object(raw_data):
        return Finding(raw_data=raw_data)

    @staticmethod
    def build_company_object(raw_data):
        compliance_claim = raw_data.get("compliance_claim", {})
        compliance_claim = none_to_default_value(compliance_claim, {})

        return Company(
            raw_data=raw_data,
            guid=raw_data.get("guid"),
            name=raw_data.get("name"),
            description=raw_data.get("description"),
            industry=raw_data.get("industry"),
            sub_industry=raw_data.get("sub_industry"),
            certifications=convert_list_to_comma_string(
                [
                    cert.get("name")
                    for cert in compliance_claim.get("certifications", [])
                ]
            ),
            display_url=raw_data.get("display_url"),
            rating=raw_data.get("rating"),
        )

    def build_vulnerability_statistics(self, raw_data):
        return [
            VulnerabilityStats(
                raw_data=stat_json,
                start_date=stat_json.get("start_date"),
                end_date=stat_json.get("end_date"),
                vulnerabilities=[
                    self.build_vulnerability_object(item_json)
                    for item_json in stat_json.get("stats", [])
                ],
            )
            for stat_json in raw_data
        ]

    @staticmethod
    def build_vulnerability_object(raw_data):
        return Vulnerability(
            raw_data=raw_data,
            id=raw_data.get("id"),
            name=raw_data.get("name"),
            first_seen=raw_data.get("first_seen"),
            event_count=raw_data.get("event_count"),
            host_count=raw_data.get("host_count"),
            confidence=raw_data.get("confidence"),
        )

    @staticmethod
    def build_highlight_object(raw_data):
        return Highlight(raw_data=raw_data)

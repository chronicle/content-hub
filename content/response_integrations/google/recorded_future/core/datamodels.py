# ============================================================================#
# title           :datamodels.py
# description     :This module contains the DataModel for entity enrichment and related entities actions
# author          :severins@siemplify.co
# date            :13-11-2019
# python_version  :3.7
# libraries       :
# requirements    :
# product_version :
# ============================================================================#

from __future__ import annotations
from .constants import DEFAULT_DEVICE_VENDOR, SEVERITY_MAP, ENRICHMENT_DATA_PREFIX
import uuid
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time, add_prefix_to_dict
from TIPCommon import dict_to_flat


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class IP:
    def __init__(
        self,
        raw_data=None,
        score=None,
        riskString=None,
        firstSeen=None,
        lastSeen=None,
        city=None,
        country=None,
        asn=None,
        organization=None,
        intelCard=None,
        criticality=None,
        rules=None,
        related_entities=[],
        evidence_details=[],
    ):
        self.raw_data = raw_data
        self.score = score
        self.riskString = riskString
        self.firstSeen = firstSeen
        self.lastSeen = lastSeen
        self.city = city
        self.country = country
        self.asn = asn
        self.organization = organization
        self.intelCard = intelCard
        self.rules = rules
        self.criticality = criticality
        self.related_entities = related_entities
        self.rule_names = [
            evidence_detail.get("rule") for evidence_detail in evidence_details
        ]

    def to_csv(self):
        return {
            "Risk Score": self.score,
            "Triggered Rules": self.riskString,
            "First Reference": self.firstSeen,
            "Last Reference": self.lastSeen,
            "Geo-City": self.city,
            "Geo-Country": self.country,
            "Asn": self.asn,
            "Org": self.organization,
        }

    def to_table(self):
        return [
            {
                "Risk Score": self.score,
                "Triggered Rules": self.riskString,
                "First Reference": self.firstSeen,
                "Last Reference": self.lastSeen,
                "Geo-City": self.city,
                "Geo-Country": self.country,
                "Asn": self.asn,
                "Org": self.organization,
                "Rule Names": ",".join(rule_name for rule_name in self.rule_names),
            }
        ]

    def to_enrichment_data(self):
        enrichment_data = {}

        if self.riskString:
            enrichment_data["RF_RiskString"] = self.riskString
        if self.rules:
            enrichment_data["RF_Rules"] = self.rules
        if self.criticality:
            enrichment_data["RF_CriticalityScore"] = self.criticality

        return enrichment_data


class URL:
    def __init__(
        self,
        raw_data=None,
        score=None,
        riskString=None,
        intelCard=None,
        criticality=None,
        rules=None,
        related_entities=[],
        evidence_details=[],
    ):
        self.raw_data = raw_data
        self.score = score
        self.riskString = riskString
        self.intelCard = intelCard
        self.rules = rules
        self.criticality = criticality
        self.related_entities = related_entities
        self.rule_names = [
            evidence_detail.get("rule") for evidence_detail in evidence_details
        ]

    def to_csv(self):
        return {"Risk Score": self.score, "Triggered Rules": self.riskString}

    def to_table(self):
        return [
            {
                "Risk Score": self.score,
                "Triggered Rules": self.riskString,
                "Rule Names": ",".join(rule_name for rule_name in self.rule_names),
            }
        ]

    def to_enrichment_data(self):
        enrichment_data = {}

        if self.riskString:
            enrichment_data["RF_RiskString"] = self.riskString
        if self.rules:
            enrichment_data["RF_Rules"] = self.rules
        if self.criticality:
            enrichment_data["RF_CriticalityScore"] = self.criticality

        return enrichment_data


class CVE:
    def __init__(
        self,
        raw_data=None,
        score=None,
        riskString=None,
        firstSeen=None,
        lastSeen=None,
        intelCard=None,
        criticality=None,
        rules=None,
        related_entities=[],
        evidence_details=[],
    ):
        self.raw_data = raw_data
        self.score = score
        self.riskString = riskString
        self.firstSeen = firstSeen
        self.lastSeen = lastSeen
        self.intelCard = intelCard
        self.rules = rules
        self.criticality = criticality
        self.related_entities = related_entities
        self.rule_names = [
            evidence_detail.get("rule") for evidence_detail in evidence_details
        ]

    def to_csv(self):
        return {
            "Risk Score": self.score,
            "Triggered Rules": self.riskString,
            "First Reference": self.firstSeen,
            "Last Reference": self.lastSeen,
        }

    def to_table(self):
        return [
            {
                "Risk Score": self.score,
                "Triggered Rules": self.riskString,
                "First Reference": self.firstSeen,
                "Last Reference": self.lastSeen,
                "Rule Names": ",".join(rule_name for rule_name in self.rule_names),
            }
        ]

    def to_enrichment_data(self):
        enrichment_data = {}

        if self.riskString:
            enrichment_data["RF_RiskString"] = self.riskString
        if self.rules:
            enrichment_data["RF_Rules"] = self.rules
        if self.criticality:
            enrichment_data["RF_CriticalityScore"] = self.criticality

        return enrichment_data


class HOST:
    def __init__(
        self,
        raw_data=None,
        score=None,
        riskString=None,
        firstSeen=None,
        lastSeen=None,
        intelCard=None,
        criticality=None,
        rules=None,
        related_entities=[],
        evidence_details=[],
    ):
        self.raw_data = raw_data
        self.score = score
        self.riskString = riskString
        self.firstSeen = firstSeen
        self.lastSeen = lastSeen
        self.intelCard = intelCard
        self.criticality = criticality
        self.rules = rules
        self.related_entities = related_entities
        self.rule_names = [
            evidence_detail.get("rule") for evidence_detail in evidence_details
        ]

    def to_csv(self):
        return {
            "Risk Score": self.score,
            "Triggered Rules": self.riskString,
            "First Reference": self.firstSeen,
            "Last Reference": self.lastSeen,
        }

    def to_table(self):
        return [
            {
                "Risk Score": self.score,
                "Triggered Rules": self.riskString,
                "First Reference": self.firstSeen,
                "Last Reference": self.lastSeen,
                "Rule Names": ",".join(rule_name for rule_name in self.rule_names),
            }
        ]

    def to_enrichment_data(self):
        enrichment_data = {}

        if self.riskString:
            enrichment_data["RF_RiskString"] = self.riskString

        return enrichment_data


class HASH:
    def __init__(
        self,
        raw_data=None,
        score=None,
        riskString=None,
        firstSeen=None,
        hashAlgorithm=None,
        lastSeen=None,
        intelCard=None,
        criticality=None,
        rules=None,
        related_entities=[],
        evidence_details=[],
    ):
        self.raw_data = raw_data
        self.score = score
        self.riskString = riskString
        self.hashAlgorithm = hashAlgorithm
        self.firstSeen = firstSeen
        self.lastSeen = lastSeen
        self.intelCard = intelCard
        self.rules = rules
        self.criticality = criticality
        self.related_entities = related_entities
        self.rule_names = [
            evidence_detail.get("rule") for evidence_detail in evidence_details
        ]

    def to_csv(self):
        return {
            "Risk Score": self.score,
            "Triggered Rules": self.riskString,
            "Hash Algorithm": self.riskString,
            "First Reference": self.firstSeen,
            "Last Reference": self.lastSeen,
        }

    def to_table(self):
        return [
            {
                "Risk Score": self.score,
                "Triggered Rules": self.riskString,
                "First Reference": self.firstSeen,
                "Last Reference": self.lastSeen,
                "Hash Algorithm": self.hashAlgorithm,
                "Rule Names": ",".join(rule_name for rule_name in self.rule_names),
            }
        ]

    def to_enrichment_data(self):
        enrichment_data = {}

        if self.riskString:
            enrichment_data["RF_RiskString"] = self.riskString
        if self.rules:
            enrichment_data["RF_Rules"] = self.rules
        if self.criticality:
            enrichment_data["RF_CriticalityScore"] = self.criticality
        if self.hashAlgorithm:
            enrichment_data["RF_HashAlgorithm"] = self.hashAlgorithm

        return enrichment_data


class Related_Entities:
    def __init__(
        self,
        raw_data=None,
        relatedEntities=None,
        intelCard=None,
        name=None,
        entity_type=None,
        count=None,
    ):
        self.raw_data = raw_data
        self.relatedEntities = relatedEntities
        self.intelCard = intelCard
        self.name = name
        self.entity_type = entity_type
        self.count = count

    def to_table(self):
        return {"Name": self.name, "Type": self.entity_type, "Count": self.count}


class Alert(BaseModel):
    def __init__(self, raw_data, id, title, rule, rule_name, triggered, severity):
        super(Alert, self).__init__(raw_data)
        self.id = id
        self.uuid = uuid.uuid4()
        self.title = title
        self.rule = rule
        self.rule_name = rule_name
        self.triggered = convert_string_to_unix_time(triggered)
        self.severity = severity

    def get_alert_info(self, alert_info, environment_common):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.title
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = DEFAULT_DEVICE_VENDOR
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.rule_name
        alert_info.start_time = self.triggered
        alert_info.end_time = self.triggered
        alert_info.events = self.create_events()

        return alert_info

    def create_events(self):
        return [dict_to_flat(self.raw_data)]

    def get_siemplify_severity(self):
        return SEVERITY_MAP.get(self.severity, 60)


class CommonData:
    def __init__(
        self,
        raw_data=None,
        entity_id=None,
        entity_name=None,
        entity_type=None,
        entity_description=None,
        risk_level=None,
        risk_score=None,
        risk_rule_count=None,
        risk_rule_most_critical=None,
    ):
        self.raw_data = raw_data
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.entity_type = entity_type
        self.entity_description = entity_description
        self.risk_level = risk_level
        self.risk_score = risk_score
        self.risk_rule_count = risk_rule_count
        self.risk_rule_most_critical = risk_rule_most_critical

    def to_enrichment_data(self):
        enrichment_data = {}

        if self.entity_id:
            enrichment_data["id"] = self.entity_id
        if self.entity_name:
            enrichment_data["name"] = self.entity_name
        if self.entity_type:
            enrichment_data["type"] = self.entity_type
        if self.entity_description:
            enrichment_data["description"] = self.entity_description
        if self.risk_level:
            enrichment_data["risk_level"] = self.risk_level
        if self.risk_score:
            enrichment_data["risk_score"] = self.risk_score
        if self.risk_rule_count:
            enrichment_data["number_of_matched_rules"] = self.risk_rule_count
        if self.risk_rule_most_critical:
            enrichment_data["most_critical_rule"] = self.risk_rule_most_critical

        return add_prefix_to_dict(enrichment_data, ENRICHMENT_DATA_PREFIX)

    def to_json(self):
        return self.raw_data


class AlertDetails:
    def __init__(self, raw_data=None, alert_url=None):
        self.raw_data = raw_data
        self.alert_url = alert_url

    def to_json(self):
        return self.raw_data


class AnalystNote:
    def __init__(self, raw_data=None, document_id=None):
        self.raw_data = raw_data
        self.document_id = document_id

    def to_enrichment_data(self, document_id=None):
        enrichment_data = {}

        if document_id:
            enrichment_data["doc_id"] = document_id

        return add_prefix_to_dict(enrichment_data, ENRICHMENT_DATA_PREFIX)

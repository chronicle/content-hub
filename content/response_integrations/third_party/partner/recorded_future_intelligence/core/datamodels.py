############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

import copy
import html
import uuid
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_datetime_to_unix_time,
)
from TIPCommon.transformation import dict_to_flat

from .constants import (
    CLASSIC_ALERT_PRODUCT,
    DEFAULT_DEVICE_VENDOR,
    ENRICHMENT_DATA_PREFIX,
    INSIKT_VULNERABILITY_NOTE_HTML,
    PBA_SEVERITY_MAP,
    PLAYBOOK_ALERT_PRODUCT,
    SEVERITY_MAP,
)
from .UtilsManager import format_timestamp


class BaseModel:
    """Base model for inheritance."""

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        """Returns JSON data."""
        return self.raw_data


class RFIndicator(BaseModel):
    """Base RF Indicator for inheritance."""

    def __init__(
        self,
        raw_data=None,
        entity_id=None,
        score=None,
        riskString=None,
        firstSeen=None,
        lastSeen=None,
        intelCard=None,
        criticality=None,
        links=[],
        evidence_details=[],
    ):
        self.raw_data = (raw_data,)
        self.entity_id = (entity_id,)
        self.score = score
        self.riskString = riskString
        self.firstSeen = firstSeen
        self.lastSeen = lastSeen
        self.intelCard = intelCard
        self.criticality = criticality
        self.links = links
        self.rule_names = [evidence_detail.get("rule") for evidence_detail in evidence_details]
        self.evidence_details = evidence_details

    def to_csv(self):
        """Returns indicator in CSV format."""
        return {
            "Risk Score": self.score,
            "Triggered Rules": self.riskString,
            "First Reference": self.firstSeen,
            "Last Reference": self.lastSeen,
        }

    def to_overview_table(self):
        """Returns indicator in table format."""
        return [
            {
                "Risk Score": self.score,
                "Triggered Rules": self.riskString,
                "First Reference": self.firstSeen,
                "Last Reference": self.lastSeen,
            },
        ]

    def to_risk_table(self):
        """Returns Evidence Details in table format."""
        return [
            {
                "Rule": rule.get("rule"),
                "Criticality": rule.get("criticalityLabel"),
                "Evidence": rule.get("evidenceString"),
                "Timestamp": rule.get("timestamp"),
            }
            for rule in self.evidence_details[::-1]
        ]

    def to_links_table(self):
        """Returns Links Details in table format."""
        return [
            {
                "Entity": entity.name,
                "Type": entity.type_,
                "Relationship": section_name,
            }
            for section_name, entities in self.links.items()
            for entity in entities
        ]

    def get_enrichment_data(self):
        """Returns indicator enrichment data."""
        return {
            "intel_card": self.intelCard,
            "risk_string": self.riskString,
            "risk_rules": ",".join(self.rule_names),
            "risk_score": self.score,
        }

    def to_enrichment_data(self):
        """Returns indicator enrichment data with prefix."""
        clean_enrichment_data = {k: v for k, v in self.get_enrichment_data().items() if v}
        return add_prefix_to_dict(clean_enrichment_data, "RF")

    def to_json(self):
        """Returns indicator json."""
        raw_data = copy.deepcopy(self.raw_data[0])
        if "links" in raw_data:
            raw_data["links"] = self.links
        return (raw_data,)


class IP(RFIndicator):
    """IP Indicator."""

    def __init__(
        self,
        raw_data=None,
        entity_id=None,
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
        links=[],
        evidence_details=[],
    ):
        super().__init__(
            raw_data,
            entity_id,
            score,
            riskString,
            firstSeen,
            lastSeen,
            intelCard,
            criticality,
            links,
            evidence_details,
        )
        self.city = city
        self.country = country
        self.asn = asn
        self.organization = organization

    def to_csv(self):
        """Returns IP indicator in CSV format."""
        return {
            "Risk Score": self.score,
            "Triggered Rules": self.riskString,
            "Geo-City": self.city,
            "Geo-Country": self.country,
            "Asn": self.asn,
            "Org": self.organization,
        }

    def to_overview_table(self):
        """Returns IP indicator in table format."""
        return [
            {
                "Risk Score": self.score,
                "Triggered Rules": self.riskString,
                "Geo-City": self.city,
                "Geo-Country": self.country,
                "Asn": self.asn,
                "Org": self.organization,
            },
        ]

    def get_enrichment_data(self):
        """Returns IP indicator enrichment data."""
        return {
            "intel_card": self.intelCard,
            "risk_string": self.riskString,
            "risk_rules": ",".join(self.rule_names),
            "risk_score": self.score,
            "city": self.city,
            "country": self.country,
            "asn": self.asn,
            "org": self.organization,
        }


class URL(RFIndicator):
    """URL Indicator."""


class CVE(RFIndicator):
    """CVE Indicator."""


class HOST(RFIndicator):
    """Host Indicator."""


class HASH(RFIndicator):
    """Hash Indicator."""

    def __init__(
        self,
        raw_data=None,
        entity_id=None,
        score=None,
        riskString=None,
        firstSeen=None,
        lastSeen=None,
        hashAlgorithm=None,
        intelCard=None,
        criticality=None,
        links=[],
        evidence_details=[],
    ):
        super().__init__(
            raw_data,
            entity_id,
            score,
            riskString,
            firstSeen,
            lastSeen,
            intelCard,
            criticality,
            links,
            evidence_details,
        )
        self.hashAlgorithm = hashAlgorithm

    def to_csv(self):
        """Returns Hash indicator in CSV format."""
        return {
            "Risk Score": self.score,
            "Triggered Rules": self.riskString,
            "Hash Algorithm": self.riskString,
            "First Reference": self.firstSeen,
            "Last Reference": self.lastSeen,
        }

    def to_overview_table(self):
        """Returns Hash indicator in table format."""
        return [
            {
                "Risk Score": self.score,
                "Triggered Rules": self.riskString,
                "First Reference": self.firstSeen,
                "Last Reference": self.lastSeen,
                "Hash Algorithm": self.hashAlgorithm,
            },
        ]


class HashReport(BaseModel):
    """Hash from Malware Report."""

    def __init__(self, raw_data, sha256, found, reports_summary, start_date, end_date):
        super(HashReport, self).__init__(raw_data)
        self.id = sha256
        self.found = found
        self.reports_summary = reports_summary
        self.start_date = start_date
        self.end_date = end_date


class Alert(BaseModel):
    """Alert."""

    def __init__(
        self,
        raw_data,
        id_,
        title,
        rule,
        rule_name,
        triggered,
        severity,
        triggered_by=None,
    ):
        super(Alert, self).__init__(raw_data)
        self.id = id_
        self.uuid = uuid.uuid4()
        self.title = title
        self.rule = rule
        self.rule_name = rule_name
        self.triggered = convert_datetime_to_unix_time(triggered)
        self.severity = severity
        self.triggered_by = triggered_by or []
        self.events = []

    def get_alert_info(self, alert_info, environment_common):
        """Returns AlertInfo object from Recorded Future Alert."""
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data),
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.title
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = CLASSIC_ALERT_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.rule_name
        alert_info.start_time = self.triggered
        alert_info.end_time = self.triggered
        alert_info.events = self.create_events()

        return alert_info

    def create_events(self):
        """Returns Recorded Future Alerts formatted as Events."""
        return [dict_to_flat(event) for event in self.events]

    def get_siemplify_severity(self):
        """Returns Alert severity."""
        return SEVERITY_MAP.get(self.severity, 60)


class AlertDetails:
    """Alert Details."""

    def __init__(self, raw_data=None, alert_url=None):
        self.raw_data = raw_data
        self.alert_url = alert_url

    def to_json(self):
        """Returns Alert Details json."""
        return self.raw_data


class AnalystNote:
    """Analyst Note."""

    def __init__(self, raw_data=None, document_id=None):
        self.raw_data = raw_data
        self.document_id = document_id

    def to_enrichment_data(self, document_id=None):
        """Returns Analyst Note data with prefix."""
        enrichment_data = {}

        if document_id:
            enrichment_data["doc_id"] = document_id

        return add_prefix_to_dict(enrichment_data, ENRICHMENT_DATA_PREFIX)


class PlaybookAlert(BaseModel):
    """PlaybookAlert."""

    def __init__(
        self,
        raw_data,
        id_,
        alert_url,
        category,
        label,
        start,
        end,
        title,
        priority,
        linked_cases=None,
        severity=None,
    ):
        super(PlaybookAlert, self).__init__(raw_data)
        self.id = id_
        self.linked_cases = linked_cases
        self.alert_url = alert_url
        self.uuid = uuid.uuid4()
        self.category = category
        self.start = convert_datetime_to_unix_time(start)
        self.end = convert_datetime_to_unix_time(end)
        self.label = label
        self.title = title
        self.priority = priority
        self.severity = severity

    def get_alert_info(self, alert_info, environment_common):
        """Returns AlertInfo object from Recorded Future Playbook Alert."""
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data),
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.title
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = PLAYBOOK_ALERT_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.label
        alert_info.start_time = self.start
        alert_info.end_time = self.end
        alert_info.events = self.create_event()

        return alert_info

    def get_siemplify_severity(self):
        """Returns Alert severity."""
        if self.severity and self.severity in SEVERITY_MAP:
            return SEVERITY_MAP.get(self.severity)
        if self.priority and self.priority in PBA_SEVERITY_MAP:
            return SEVERITY_MAP.get(PBA_SEVERITY_MAP.get(self.priority), 60)
        return 60

    def create_event(self):
        """Returns Recorded Future Playbook Alert formatted as Events."""
        event = copy.deepcopy(self.raw_data)
        event["category"] = self.category
        if self.linked_cases is not None:
            event["linked_cases"] = self.linked_cases
        return [dict_to_flat(event)]

    def create_events_with_html(self):
        """Creates event with HTML chunks to be inserted in widgets."""
        event = copy.deepcopy(self.raw_data)
        event["category"] = self.category
        if self.linked_cases is not None:
            event["linked_cases"] = self.linked_cases
        if self.category == "domain_abuse":
            self.add_targets_html_domain_abuse(event)
            self.add_assessment_html_domain_abuse(event)
            self.add_dns_html(event)
            self.add_whois_html(event)
        elif self.category == "code_repo_leakage":
            self.add_targets_html(event)
            self.add_assessment_html_code_repo(event)
        elif self.category == "cyber_vulnerability":
            self.add_targets_html(event)
            self.add_insikt_vuln_html(event)
            self.add_affected_products_html(event)
        elif self.category == "identity_novel_exposures":
            self.add_targets_html(event)
            self.add_hashes_html(event)
            self.add_secret_html(event)
            self.add_av_html(event)
        elif self.category == "third_party_risk":
            self.add_targets_html(event)
            self.add_assessment_html_tpr(event)
        return event

    def add_assessment_html_tpr(self, event):
        """Adds HTML panel for assessments.

        :param event {dict}: raw event object to append html chunks to
        """
        chunk = """
        <div class="assessment">
            <p><span class="label">Assessment:</span> {}</p>
            <p><span class="label">Criticality:</span> {}</p>
            <p><span class="label">Summary:</span> {}</p>
            <p><span class="label">Added:</span>  {}</p>
            <p><span class="label">Triggered Risk Rules:</span> {}</p>
            <div class="divider"></div>
        </div>
        """
        assessment_html = []

        for assessment in event.get("panel_evidence_summary", {}).get(
            "assessments",
            [],
        ):
            try:
                rules = " | ".join(
                    [rule["name"] for rule in assessment.get("evidence", {}).get("data", [])],
                )
                new_chunk = chunk.format(
                    assessment["risk_rule"],
                    assessment["level"],
                    assessment["evidence"]["summary"],
                    format_timestamp(assessment["added"]),
                    rules,
                )
                assessment_html.append(new_chunk)
            except KeyError:
                continue
        event["assessment_html"] = "\n\n".join(assessment_html)

    def add_insikt_vuln_html(self, event):
        """Adds HTML panel for Insikt notes for Vulns.

        :param event {dict}: raw event object to append html chunks to
        """
        insikt_html = []
        for note in event.get("panel_evidence_summary", {}).get("insikt_notes", []):
            try:
                new_chunk = INSIKT_VULNERABILITY_NOTE_HTML.format(
                    note["title"],
                    note["published"],
                    note["topic"],
                    note["fragment"],
                    note["id"],
                    note["id"],
                )
                insikt_html.append(new_chunk)
            except KeyError:
                continue
        event["insikt_html"] = "\n".join(insikt_html)

    def add_affected_products_html(self, event):
        """Adds HTML panel for affected products.

        :param event {dict}: raw event object to append html chunks to
        """
        chunk = """
            <li>{}</li>
        """
        affected_products_html = []
        for product in event.get("panel_evidence_summary", {}).get(
            "affected_products",
            [],
        ):
            try:
                affected_products_html.append(chunk.format(product["name"]))
            except KeyError:
                continue
        event["affected_products_html"] = "\n".join(affected_products_html)

    def add_hashes_html(self, event):
        """Adds HTML panel for file hashes.

        :param event {dict}: raw event object to append html chunks to
        """
        chunk = """
            <li><span class="label">{}:</span> {} </li>
        """
        hashes_html = []
        for hash_ in (
            event.get("panel_evidence_summary", {}).get("exposed_secret", {}).get("hashes", [])
        ):
            try:
                hashes_html.append(chunk.format(hash_["algorithm"], hash_["hash"]))
            except KeyError:
                continue
        event["hashes_html"] = "\n".join(hashes_html)

    def add_secret_html(self, event):
        """Adds HTML panel for secrets.

        :param event {dict}: raw event object to append html chunks to
        """
        chunk = """
            <li>{}</li>
        """
        secrets_html = []
        for prop in (
            event.get("panel_evidence_summary", {})
            .get("exposed_secret", {})
            .get("details", {})
            .get("properties", [])
        ):
            try:
                secrets_html.append(chunk.format(prop))
            except KeyError:
                continue
        event["secrets_html"] = "\n".join(secrets_html)

    def add_av_html(self, event):
        """Adds HTML panel for antivirus.

        :param event {dict}: raw event object to append html chunks to
        """
        chunk = """
            <li>{}</li>
        """
        av_html = []
        for prop in (
            event.get("panel_evidence_summary", {}).get("compromised_host", {}).get("antivirus", [])
        ):
            try:
                av_html.append(chunk.format(prop))
            except KeyError:
                continue
        event["av_html"] = "\n".join(av_html)

    def add_targets_html_domain_abuse(self, event):
        """Adds HTML panel for targets.

        :param event {dict}: raw event object to append html chunks to
        """
        chunk = "<li>{}</li>"
        target_html = []

        for target in event.get("panel_status", {}).get("targets", []):
            try:
                target_html.append(chunk.format(target))
            except KeyError:
                continue
        event["targets_html"] = " ".join(target_html)

    def add_targets_html(self, event):
        """Adds HTML panel for targets.

        :param event {dict}: raw event object to append html chunks to
        """
        chunk = "<li>{}</li>"
        target_html = []
        for target in event.get("panel_status", {}).get("targets", []):
            with suppress(KeyError):
                target_html.append(chunk.format(target["name"]))
        event["targets_html"] = " ".join(target_html)

    def add_assessment_html_code_repo(self, event):
        """Adds HTML panel for assessments.

        :param event {dict}: raw event object to append html chunks to
        """
        divider = (
            '\n<div class="section-content" style="font-family: '
            "'Source Sans Pro', 'Noto Sans', sans-serif;\">\n"
        )

        chunk = """
        <div class="assessment">
            <p><span class="label">Assessment Type:</span> {}</p>
            <p><span class="label">Assessment Keyword:</span> {}</p>
            <p><span class="label">Seen on File:</span> {}</p>
            <p><span class="label">Published Date:</span> {}</span></p>
            <p><span class="label">File Content:</span></p>
            <pre><code>{}</code></pre>
            <div class="divider"></div>
        </div>
        """

        assessment_html = []
        for evidence in event.get("panel_evidence_summary", {}).get("evidence", []):
            for assessment in evidence.get("assessments", []):
                try:
                    new_chunk = chunk.format(
                        assessment["title"],
                        assessment["value"],
                        evidence["url"],
                        format_timestamp(evidence["published"]),
                        html.escape(evidence["content"]),
                    )
                    assessment_html.append(new_chunk)
                except KeyError:
                    continue
        event["assessment_html"] = divider.join(assessment_html)

    def add_assessment_html_domain_abuse(self, event):
        """Adds HTML for domain abuse assessments.

        :param event {dict}: raw event object to append html chunks to"
        """
        chunk = "<li>{}</li>"
        assessment_html = []

        for assessment in event.get("panel_status", {}).get("context_list", []):
            try:
                assessment_html.append(chunk.format(assessment["context"]))
            except KeyError:
                continue
        event["assessment_html"] = " ".join(assessment_html)

    def add_dns_html(self, event):
        """Adds HTML for DNS records.

        :param event {dict}: raw event object to append html chunks to"
        """
        chunk = "<li>{} ({}) - {} Record - {}</li>"
        dns_html = []

        for record in event.get("panel_evidence_summary", {}).get(
            "resolved_record_list",
            [],
        ):
            with suppress(KeyError):
                dns_html.append(
                    chunk.format(
                        record["entity"].split(":")[-1],
                        record["risk_score"],
                        record["record_type"],
                        ", ".join(
                            [context["context"] for context in record["context_list"]],
                        ),
                    ),
                )
        event["dns_html"] = " ".join(dns_html)

    def add_whois_html(self, event):
        """Adds HTML for Whois records.

        :param event {dict}: raw event object to append html chunks to"
        """
        whois_html = """
            <p><span class="label">Created Date:</span> {}</p>
            <p><span class="label">Registrar Name:</span> {}</p>
            <p><span class="label">Name Servers:</span></p>
            <ul>
                {}
            </ul>
            <p><span class="label">Private Registration:</span> {}</p>

        """

        for record in event.get("panel_evidence_whois", {}).get("body", []):
            if record.get("attribute") == "attr:whois":
                value = record.get("value", {})

                ns_html = []
                for ns in value.get("nameServers", []):
                    try:
                        ns_html.append("<li>{}</li>".format(ns.split(":")[-1]))
                    except KeyError:
                        continue
                ns_html = " ".join(ns_html)

                if created_date := value.get("createdDate", ""):
                    created_date = format_timestamp(created_date)

                event["whois_html"] = whois_html.format(
                    created_date,
                    value.get("registrarName", ""),
                    ns_html,
                    value.get("privateRegistration"),
                )


@dataclass
class ActionResult:
    """ActionResult dataclass."""

    output_message: str
    result_value: bool | str
    json_result: dict[str, Any] = None
    table_results: dict[str, list[dict[str, Any]]] | list[dict[str, Any]] = None

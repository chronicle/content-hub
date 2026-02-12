############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

import re
from collections import defaultdict
from contextlib import suppress
from itertools import chain
from typing import TYPE_CHECKING

from psengine.constants import TIMESTAMP_STR
from psengine.enrich import (
    EnrichedDomain,
    EnrichedHash,
    EnrichedIP,
    EnrichedURL,
    EnrichedVulnerability,
    SOAREnrichedEntity,
)
from psengine.malware_intel import SandboxReport
from psengine.playbook_alerts import PBA_Generic, PBA_IdentityNovelExposure

from .constants import (
    ENTITY_DOMAIN,
    ENTITY_EMAIL,
    ENTITY_HASH,
    ENTITY_IP,
    ENTITY_URL,
    ENTITY_VULN,
)
from .datamodels import (
    CVE,
    HASH,
    HOST,
    IP,
    URL,
    Alert,
    AlertDetails,
    AnalystNote,
    HashReport,
    PlaybookAlert,
)
from .exceptions import RecordedFutureDataModelTransformationLayerError

if TYPE_CHECKING:
    from psengine.classic_alerts import ClassicAlert, ClassicAlertHit
    from psengine.classic_alerts.classic_alert import EnrichedEntity, TriggeredBy
    from psengine.enrich import (
        EnrichedDomain,
        EnrichedHash,
        EnrichedIP,
        EnrichedVulnerability,
    )

ENTITY_DATAMODEL_MAP = {
    "ip": IP,
    "domain": HOST,
    "hash": HASH,
    "url": URL,
    "vulnerability": CVE,
}

SOAR_ENTITY_DATAMODEL_MAP = {
    "IpAddress": IP,
    "InternetDomainName": HOST,
    "Hash": HASH,
    "URL": URL,
    "CyberVulnerability": CVE,
}


def dump_model(model, **kwargs):
    return model.model_dump(
        by_alias=True, mode="json", exclude_none=True, exclude_unset=True, **kwargs
    )


def build_links(links):
    """Flattens and reformats links object.
    :param links: {dict} Object containing links info from API.
    """
    if not links:
        return {}

    new_links = defaultdict(list)
    for hit in links.hits:
        for section in hit.sections:
            if section.section_id and section.section_id.name:
                section_name = section.section_id.name
                for list_ in section.lists:
                    new_links[section_name].extend(list_.entities)
    return new_links


def build_siemplify_object(
    enriched_entity: EnrichedIP
    | EnrichedVulnerability
    | EnrichedHash
    | EnrichedDomain
    | EnrichedURL,
) -> CVE | HASH | HOST | IP | URL:
    """Create enriched entity datamodel object.

    Args:
        enriched_entity (Enriched*): psengine enriched entity model

    Returns
    -------
        entity (CVE | HASH | HOST | IP | URL): SecOps enriched entity object
    """
    entity_data = {
        "raw_data": dump_model(enriched_entity.content),
        "entity_id": enriched_entity.content.entity.id_,
        "score": enriched_entity.content.risk.score,
        "riskString": enriched_entity.content.risk.risk_string,
        "firstSeen": enriched_entity.content.timestamps.first_seen,
        "lastSeen": enriched_entity.content.timestamps.last_seen,
        "intelCard": enriched_entity.content.intel_card,
        "criticality": enriched_entity.content.risk.criticality,
        "links": build_links(enriched_entity.content.links),
        "evidence_details": [dump_model(e) for e in enriched_entity.content.risk.evidence_details],
    }
    if enriched_entity.entity_type == "ip" and enriched_entity.content.location is not None:
        entity_data["city"] = enriched_entity.content.location.location.city
        entity_data["country"] = enriched_entity.content.location.location.country
        entity_data["asn"] = enriched_entity.content.location.asn
        entity_data["organization"] = enriched_entity.content.location.organization
    if enriched_entity.entity_type == "hash":
        entity_data["hashAlgorithm"] = enriched_entity.content.hash_algorithm
    return ENTITY_DATAMODEL_MAP[enriched_entity.entity_type](**entity_data)


def build_siemplify_soar_object(soar_enriched: SOAREnrichedEntity) -> CVE | HASH | HOST | IP | URL:
    """Create enriched entity datamodel object for SOAR response.

    Args:
        soar_enriched (SOAREnrichedEntity): psengine enriched entity model from SOAR

    Returns
    -------
        entity (CVE | HASH | HOST | IP | URL): SecOps enriched entity object
    """
    entity_type = soar_enriched.content.entity.type_
    entity_data = {
        "raw_data": dump_model(soar_enriched.content),
        "entity_id": soar_enriched.content.entity.id_,
        "score": soar_enriched.content.risk.score,
    }
    if soar_enriched.content.risk.rule.evidence is not None:
        entity_data["evidence_details"] = [
            dump_model(e) for e in soar_enriched.content.risk.rule.evidence
        ]
    return SOAR_ENTITY_DATAMODEL_MAP[entity_type](**entity_data)


def build_siemplify_hash_report_object(
    sha256: str,
    reports: list[SandboxReport] | dict,
    start_date,
    end_date,
) -> HashReport:
    """Create Hash object from Malware report.

    Args:
        report: Sandbox Report

    Returns
    -------
        HashReport object, one per report of each hash.
    """
    if isinstance(reports, dict):
        return HashReport(
            raw_data=reports,
            sha256=sha256,
            found=False,
            reports_summary=[],
            start_date=start_date,
            end_date=end_date,
        )

    final_reports = []
    for report in reports:
        data = {
            "id": report.sample.id,
            "score": report.sample.score,
            "tags": report.sample.tags,
            "completed": report.sample.completed,
            "net_flows": [],
            "signatures": [],
            "extensions": report.static.exts,
        }

        for flow in report.dynamic.network.flows:
            if not flow.dst_ip:
                continue

            data["net_flows"].append({
                "dst_ip": flow.dst_ip,
                "dst_port": flow.dst_port,
                "layer_7": ", ".join(flow.layer_7),
                "proto": flow.proto,
            })

        for sign in report.dynamic.signatures:
            if not sign.desc:
                continue

            data["signatures"].append({
                "descr": sign.desc,
                "name": sign.name,
                "score": sign.score,
                "tags": ", ".join(sign.tags),
                "ttps": ", ".join(sign.ttp),
            })
        final_reports.append(data)

    return HashReport(
        raw_data=[dump_model(report) for report in reports],
        sha256=sha256,
        found=True,
        reports_summary=final_reports,
        start_date=start_date,
        end_date=end_date,
    )


def format_triggered_by(data):
    """Formats triggered by into a dictionary with flattened values.
    :param data: {list} triggered_by object from Alert API
    : return {list}.
    """
    if not data:
        return {}
    results = {}
    for triggered_by in data:
        try:
            new_path = []
            path = triggered_by["entity_paths"][0]
            for entity in path:
                new_entity = entity.get("entity")
                if not new_entity:
                    continue
                new_entity["relationship"] = entity.get("attribute", {}).get("id")
                new_path.append(new_entity)
            results[triggered_by["reference_id"]] = new_path
        except KeyError:
            continue
    return results


def build_event(
    hit: ClassicAlertHit,
    triggered_by: list[TriggeredBy],
    triggered_by_str: list[str],
    enriched_entities: list[EnrichedEntity],
    extract_all_entities,
):
    """Formats and builds event out of Alert reference.
    :param triggered: {dict} triggered_by object from Alert API
    : param triggered_by: {list} raw triggered_by info from RFAPI
    : return {dict}.
    """
    entity_data = []
    raw_data = {}
    raw_data["triggered_by"] = triggered_by
    raw_data["triggered_by_string"] = triggered_by_str

    if extract_all_entities:
        entity_data = hit.entities
        if not entity_data:
            entity_data = list(
                set(
                    chain.from_iterable(
                        ref.entities for ent in enriched_entities for ref in ent.references
                    ),
                ),
            )
        entity_data = [dump_model(e) for e in entity_data]
    elif value := _extract_triggered_by(triggered_by_str):
        entity_data = [value[0]]

    for k, v in [
        (ENTITY_IP, "IpAddress"),
        (ENTITY_DOMAIN, "InternetDomainName"),
        (ENTITY_EMAIL, "EmailAddress"),
        (ENTITY_HASH, "Hash"),
        (ENTITY_URL, "URL"),
        (ENTITY_VULN, "CyberVulnerability"),
    ]:
        raw_data[k] = ",".join(
            [entity["name"] for entity in entity_data if entity["type"] == v],
        )

    return raw_data


def build_alert(
    raw_alert: ClassicAlert,
    severity,
    extract_all_entities,
    ai_insights_text=None,
):
    """Build Alert object.
    :param events: {list} Alert events from raw events.
    :param severity: {str} Severity to assign to alert.
    :return: {Alert} The Alert object.
    """
    raw_data = dump_model(raw_alert)
    raw_data["ai_insights_text"] = ai_insights_text
    alert = Alert(
        raw_data=raw_data,
        id_=raw_alert.id_,
        title=raw_alert.title,
        rule=raw_alert.rule.id_,
        rule_name=raw_alert.rule.name,
        triggered=raw_alert.log.triggered,
        severity=severity,
    )

    try:
        for hit in raw_alert.hits:
            triggered_by = raw_alert.triggered_by_from_hit(hit)
            alert.events.append(
                build_event(
                    hit,
                    _extract_triggered_by(triggered_by),
                    triggered_by,
                    raw_alert.enriched_entities,
                    extract_all_entities,
                ),
            )
    except (KeyError, IndexError) as err:
        raise RecordedFutureDataModelTransformationLayerError(err)
    return alert


def build_playbook_alert(pba: PBA_Generic, linked_cases=None, severity=None):
    """Build PBA object.
    :param playbook_alert: {psengine.playbook_alerts.base_playbook_alert} PBA object.
    :param linked_cases: {list} Duplicate cases from the same playbook alert
    :param severity: {str} Severity to assign to alert.
    """
    id_ = pba.playbook_alert_id
    alert_url = f"https://app.recordedfuture.com/portal/playbook-alerts/{id_}"

    # when the compromised user isn't an email
    entity_name = pba.panel_status.entity_name
    if entity_name is None and isinstance(pba, PBA_IdentityNovelExposure):
        entity_name = pba.panel_evidence_summary.subject

    return PlaybookAlert(
        raw_data=dump_model(pba),
        id_=id_,
        alert_url=alert_url,
        category=pba.category,
        label=pba.panel_status.case_rule_label,
        start=pba.panel_status.created,
        end=pba.panel_status.updated,
        title=f"{pba.panel_status.case_rule_label} - {entity_name}",
        priority=pba.panel_status.priority,
        linked_cases=linked_cases,
        severity=severity,
    )


def build_siemplify_analyst_note_object(response):
    return AnalystNote(raw_data=dump_model(response), document_id=response.note_id)


def build_siemplify_alert_object_old(references, triggered_by):
    triggered_by = format_triggered_by(triggered_by)
    alert = references[0].pop("alert")
    alert["hits"] = []
    for ref in references:
        alert["rule"] = ref.pop("rule")
        alert["counts"] = ref.pop("counts")
        alert["review"] = ref.pop("review")
        ref["triggered_by"] = triggered_by.get(ref.get("id", ""))
        alert["hits"].append(ref)
    return AlertDetails(raw_data=alert, alert_url=alert.get("url"))


def _extract_triggered_by(triggered_by: list[str]) -> list[dict]:
    results = []
    for value in triggered_by:
        with suppress(KeyError):
            value = value.split("->")[0]
            if matches := re.split(r"(.+?)(\(\w+?\))", value, re.IGNORECASE):
                matches = [m for m in matches if m and m != " "]
                *entity, type_ = matches
                entity = " ".join(entity)
                type_ = type_.replace("(", "").replace(")", "")

                obj = {
                    "name": entity,
                    "type": type_,
                }

                if obj not in results:
                    results.append(obj)

    return results


def build_siemplify_alert_object(alert: ClassicAlert):
    org_data = {
        "organisation_id": "",
        "organisation_name": "",
    }

    if orgs := alert.owner_organisation_details.organisations:
        orgs = orgs[0]
        org_data = {
            "organisation_id": orgs.organisation_id,
            "organisation_name": orgs.organisation_name,
        }

    rule = {
        **dump_model(alert.rule, exclude="url"),
        "url": alert.rule.url.portal,
        "owner_id": alert.owner_organisation_details.owner_id,
        "owner_name": alert.owner_organisation_details.owner_name,
        **org_data,
    }

    hits = []
    for hit in alert.hits:
        note = {}
        if an := hit.analyst_note:
            note = {
                "noteId": an.id_,
                "noteLink": str(an.url.portal),
            }
        parsed_triggered_by = alert.triggered_by_from_hit(hit)
        single_hit = {
            "entities": [dump_model(e) for e in hit.entities],
            "fragment": hit.fragment,
            "id": hit.id_,
            "language": hit.language,
            **note,
            "title": hit.document.title,
            "source": dump_model(hit.document.source),
            "triggered_by": _extract_triggered_by(parsed_triggered_by),
            "triggered_by_string": parsed_triggered_by,
        }
        hits.append(single_hit)

    new_alert_obj = {
        "id": alert.id_,
        "title": alert.title,
        "triggered": alert.log.triggered.strftime(TIMESTAMP_STR),
        "url": str(alert.url.portal),
        "type": alert.type_,
        "hits": hits,
        "rule": rule,
        "review": dump_model(alert.review),
    }

    return AlertDetails(raw_data=new_alert_obj, alert_url=str(alert.url.portal))

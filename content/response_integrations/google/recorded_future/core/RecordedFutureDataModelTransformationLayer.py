# ============================================================================#
# title           :RecordedFutureDataModelTransformationLayer.py
# description     :This Module contains the TransformationLayer from the raw data based on the datamodel
# author          :severins@siemplify.co
# date            :13-10-2019
# python_version  :3.7
# libraries       :
# requirements    :
# product_version :
# ============================================================================#


# ============================= IMPORTS ===================================== #

from __future__ import annotations
from .datamodels import (
    IP,
    CVE,
    URL,
    HOST,
    HASH,
    Related_Entities,
    Alert,
    CommonData,
    AlertDetails,
    AnalystNote,
)
from .exceptions import RecordedFutureDataModelTransformationLayerError


def build_siemplify_ip_object(response, entity):
    report = response.json().get("data")

    if report:
        return IP(
            raw_data=report,
            score=report.get("risk", {}).get("score"),
            riskString=report.get("risk", {}).get("riskString"),
            firstSeen=report.get("timestamps", {}).get("firstSeen"),
            lastSeen=report.get("timestamps", {}).get("lastSeen"),
            city=report.get("location", {}).get("city"),
            country=report.get("location", {}).get("country"),
            asn=report.get("location", {}).get("asn"),
            organization=report.get("location", {}).get("organization"),
            intelCard=report.get("intelCard"),
            rules=report.get("risk", {}).get("rules"),
            criticality=report.get("risk", {}).get("criticality"),
            related_entities=build_siemplify_related_entities_objects_from_raw_data(
                report
            ),
            evidence_details=report.get("risk", {}).get("evidenceDetails", []),
        )

    raise RecordedFutureDataModelTransformationLayerError(
        f"Unable to get reputation for {entity}"
    )


def build_siemplify_cve_object(response, entity):
    report = response.json().get("data")

    if report:
        return CVE(
            raw_data=report,
            score=report.get("risk", {}).get("score"),
            riskString=report.get("risk", {}).get("riskString"),
            firstSeen=report.get("timestamps", {}).get("firstSeen"),
            lastSeen=report.get("timestamps", {}).get("lastSeen"),
            intelCard=report.get("intelCard"),
            rules=report.get("risk", {}).get("rules"),
            criticality=report.get("risk", {}).get("criticality"),
            related_entities=build_siemplify_related_entities_objects_from_raw_data(
                report
            ),
            evidence_details=report.get("risk", {}).get("evidenceDetails", []),
        )

    raise RecordedFutureDataModelTransformationLayerError(
        f"Unable to get reputation for {entity}"
    )


def build_siemplify_hash_object(response, entity):
    report = response.json().get("data")

    if report:
        return HASH(
            raw_data=report,
            score=report.get("risk", {}).get("score"),
            riskString=report.get("risk", {}).get("riskString"),
            firstSeen=report.get("timestamps", {}).get("firstSeen"),
            hashAlgorithm=report.get("hashAlgorithm"),
            lastSeen=report.get("timestamps", {}).get("lastSeen"),
            intelCard=report.get("intelCard"),
            rules=report.get("risk", {}).get("rules"),
            criticality=report.get("risk", {}).get("criticality"),
            related_entities=build_siemplify_related_entities_objects_from_raw_data(
                report
            ),
            evidence_details=report.get("risk", {}).get("evidenceDetails", []),
        )

    raise RecordedFutureDataModelTransformationLayerError(
        f"Unable to get reputation for {entity}"
    )


def build_siemplify_host_object(response, entity):
    report = response.json().get("data")

    if report:
        return HOST(
            raw_data=report,
            score=report.get("risk", {}).get("score"),
            criticality=report.get("risk", {}).get("criticality"),
            riskString=report.get("risk", {}).get("riskString"),
            firstSeen=report.get("timestamps", {}).get("firstSeen"),
            lastSeen=report.get("timestamps", {}).get("lastSeen"),
            intelCard=report.get("intelCard"),
            rules=report.get("risk", {}).get("rules"),
            related_entities=build_siemplify_related_entities_objects_from_raw_data(
                report
            ),
            evidence_details=report.get("risk", {}).get("evidenceDetails", []),
        )

    raise RecordedFutureDataModelTransformationLayerError(
        f"Unable to get reputation for {entity}"
    )


def build_siemplify_url_object(response, entity):
    report = response.json().get("data")

    if report:
        return URL(
            raw_data=report,
            score=report.get("risk", {}).get("score"),
            riskString=report.get("risk", {}).get("riskString"),
            intelCard=report.get("intelCard"),
            rules=report.get("risk", {}).get("rules"),
            criticality=report.get("risk", {}).get("criticality"),
            related_entities=build_siemplify_related_entities_objects_from_raw_data(
                report
            ),
            evidence_details=report.get("risk", {}).get("evidenceDetails", []),
        )

    raise RecordedFutureDataModelTransformationLayerError(
        f"Unable to get reputation for {entity}"
    )


def build_siemplify_related_entities_objects_from_raw_data(raw_data):
    response = []

    for related_entities in raw_data.get("relatedEntities", []):
        response = response + [
            Related_Entities(
                raw_data=raw_data,
                name=raw_data.get("entity", {}).get("name"),
                entity_type=raw_data.get("entity", {}).get("type"),
                count=raw_data.get("count"),
            )
            for raw_data in related_entities.get("entities", [])
        ]

    return response


def build_siemplify_related_entities_object(response, entity):
    report = response.json().get("data")

    if report:
        return Related_Entities(
            raw_data=report,
            relatedEntities=report.get("relatedEntities"),
            intelCard=report.get("intelCard"),
        )

    raise RecordedFutureDataModelTransformationLayerError(
        f"Unable to get related entities for {entity}"
    )


def build_related_entities_report(report):
    """
    Build related entities report .
    :param report: {dict} report received from Reported Future.
    :return: {dict} Related entities report for an entity.
    """
    dict_of_related_entities = {}

    if report.relatedEntities:
        for related_entity in report.relatedEntities:
            if related_entity.get("entities") and related_entity.get("type"):
                for type_entity in related_entity.get("entities"):
                    if type_entity.get("entity").get("name") and type_entity.get(
                        "entity"
                    ).get("type"):
                        dict_of_related_entities[related_entity.get("type")] = {
                            "entity_type": type_entity.get("entity").get("type"),
                            "entity_name": type_entity.get("entity").get("name"),
                        }

    return dict_of_related_entities


def build_alerts(raw_data, severity):
    """
    Build list of Alert objects.
    :param raw_data: {dict} Response raw data.
    :param severity: {str} Severity to assign to alerts.
    :return: {list} List of Alert objects.
    """
    return [
        build_alert(result, severity)
        for result in raw_data.get("data", {}).get("results", [])
    ]


def build_alert(data, severity):
    """
    Build Alert object.
    :param data: {dict} Alert data from raw data.
    :param severity: {str} Severity to assign to alert.
    :return: {Alert} The Alert object.
    """
    return Alert(
        raw_data=data,
        id=data.get("id"),
        title=data.get("title"),
        rule=data.get("rule", {}),
        rule_name=data.get("rule", {}).get("name", ""),
        triggered=data.get("triggered"),
        severity=severity,
    )


def get_alert(raw_data, severity):
    """
    Get Alert object.
    :param raw_data: {dict} Response raw data.
    :param severity: {str} Severity to assign to alert.
    :return: {Alert} The Alert object.
    """
    return build_alert(raw_data.get("data", {}), severity)


def build_siemplify_ioc_objects(response_json):
    data = {}
    results = response_json.get("data", {}).get("results", [])

    for entity in results:
        data[entity.get("entity", {}).get("name")] = build_siemplify_ioc_object(entity)

    return data


def build_siemplify_analyst_note_object(response_json):
    return AnalystNote(
        raw_data=response_json, document_id=response_json.get("document_id", "")
    )


def build_siemplify_ioc_object(entity):
    return CommonData(
        raw_data=entity,
        entity_id=entity.get("entity", {}).get("id"),
        entity_name=entity.get("entity", {}).get("name"),
        entity_type=entity.get("entity", {}).get("type"),
        entity_description=entity.get("entity", {}).get("description"),
        risk_level=entity.get("risk", {}).get("level"),
        risk_score=entity.get("risk", {}).get("score"),
        risk_rule_count=entity.get("risk", {}).get("rule", {}).get("count"),
        risk_rule_most_critical=entity.get("risk", {})
        .get("rule", {})
        .get("mostCritical"),
    )


def build_siemplify_alert_object(raw_data):
    return AlertDetails(
        raw_data=raw_data, alert_url=raw_data.get("data", {}).get("url")
    )

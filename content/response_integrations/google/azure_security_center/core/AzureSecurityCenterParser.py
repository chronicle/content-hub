from __future__ import annotations
from .datamodels import (
    RegulatoryStandard,
    RegulatoryControl,
    GraphAlert,
    AzureIncidentAlert,
    AzureAlert,
    AzureEntity,
)


class AzureSecurtyCenterParser:
    """
    Azure Security Center Transformation Layer.
    """

    @staticmethod
    def build_regulatory_standard_obj(raw_data):
        return RegulatoryStandard(
            raw_data=raw_data,
            state=raw_data.get("properties", {}).get("state"),
            passedControls=raw_data.get("properties", {}).get("passedControls"),
            failedControls=raw_data.get("properties", {}).get("failedControls"),
            skippedControls=raw_data.get("properties", {}).get("skippedControls"),
            unsupportedControls=raw_data.get("properties", {}).get(
                "unsupportedControls"
            ),
            **raw_data
        )

    @staticmethod
    def build_regulatory_control_obj(raw_data, standard_name=None):
        return RegulatoryControl(
            raw_data=raw_data,
            standard_name=standard_name,
            state=raw_data.get("properties", {}).get("state"),
            description=raw_data.get("properties", {}).get("description"),
            passedAssessments=raw_data.get("properties", {}).get("passedAssessments"),
            failedAssessments=raw_data.get("properties", {}).get("failedAssessments"),
            skippedAssessments=raw_data.get("properties", {}).get("skippedAssessments"),
            **raw_data
        )

    @staticmethod
    def extract_values_from_graph_alert_raw_data(raw_data):
        return [
            AzureSecurtyCenterParser.build_graph_alert_obj(raw_alert)
            for raw_alert in raw_data.get("value", [])
        ]

    @staticmethod
    def build_graph_alert_obj(raw_data):
        source = raw_data.get("sourceMaterials", [])
        return GraphAlert(
            raw_data=raw_data,
            location=source[0].rsplit("/", 1)[-1] if source else "",
            **raw_data
        )

    @staticmethod
    def build_azure_entity_obj(raw_data):
        return AzureEntity(
            raw_data=raw_data,
            id=raw_data.get("$id", ""),
            displayName=raw_data.get("displayName", ""),
            compromisedEntity=raw_data.get("compromisedEntity", ""),
            count=raw_data.get("count", 0),
            severity=raw_data.get("severity", ""),
            alertType=raw_data.get("alertType", ""),
            vendorName=raw_data.get("vendorName", ""),
            providerName=raw_data.get("providerName", ""),
            startTimeUtc=raw_data.get("startTimeUtc", ""),
            endTimeUtc=raw_data.get("endTimeUtc", ""),
            Location=raw_data.get("Location", ""),
            system_alert_ids=raw_data.get("systemAlertIds", []),
        )

    @staticmethod
    def build_azure_alert_obj(raw_data, alert_location=None):
        alert_is_incident = raw_data.get("properties", {}).get("isIncident", False)

        constructor_args = {
            "raw_data": raw_data,
            "entities_obj": [
                AzureSecurtyCenterParser.build_azure_entity_obj(entity)
                for entity in raw_data.get("properties", {}).get("entities", [])
                if not entity.get("$ref")
            ],
            "is_incident": alert_is_incident,
            "timeGeneratedUtc": raw_data.get("properties", {}).get("timeGeneratedUtc"),
            "processingEndTimeUtc": raw_data.get("properties", {}).get(
                "processingEndTimeUtc"
            ),
            "startTimeUtc": raw_data.get("properties", {}).get("startTimeUtc", ""),
            "endTimeUtc": raw_data.get("properties", {}).get("endTimeUtc", ""),
            "severity": raw_data.get("properties", {}).get("severity"),
            "alert_type": raw_data.get("properties", {}).get("alertType"),
            "description": raw_data.get("properties", {}).get("description"),
            "alert_display_name": raw_data.get("properties", {}).get(
                "alertDisplayName"
            ),
            "alert_location": alert_location,
            "alert_id": raw_data.get("properties", {}).get("systemAlertId"),
            **raw_data,
        }

        return (
            AzureIncidentAlert(**constructor_args)
            if alert_is_incident
            else AzureAlert(**constructor_args)
        )

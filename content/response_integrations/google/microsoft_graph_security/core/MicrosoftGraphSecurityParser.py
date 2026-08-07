from __future__ import annotations
from .datamodels import Alert, Incident
from TIPCommon.types import SingleJson


class MicrosoftGraphSecurityParser:
    """
    Microsoft Graph Security Transformation Layer.
    """

    @staticmethod
    def build_siemplify_alert_obj(alert_data):
        return Alert(
            raw_data=alert_data,
            vendor=alert_data.get("vendorInformation", {}).get("vendor"),
            provider=alert_data.get("vendorInformation", {}).get("provider"),
            **alert_data
        )

    @staticmethod
    def build_siemplify_incident_obj(incident_data: SingleJson) -> Incident:
        """Build incident object.

        Args:
            incident_data (SingleJson): Incident data from MsGraph Security API.

        Returns:
            Incident: Incident object.
        """
        return Incident.from_json(incident_data=incident_data)

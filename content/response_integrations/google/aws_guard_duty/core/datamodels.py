from __future__ import annotations
from TIPCommon.transformation import dict_to_flat
import uuid

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from . import consts


FILE_FORMATS = {
    "Plaintext": "TXT",
    "Structured Threat Information Expression (STIX)": "STIX",
    "Open Threat Exchange (OTX)™ CSV": "OTX_CSV",
    "FireEye™ iSIGHT Threat Intelligence CSV": "FIRE_EYE",
    "Proofpoint™ ET Intelligence Feed CSV": "PROOF_POINT",
    "AlienVault™ Reputation Feed": "ALIEN_VAULT",
}


SEVERITIES = {"INFORMATIONAL": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}


class Finding:
    """
    Finding data model.
    """

    def __init__(
        self,
        raw_data,
        detector_id,
        created_at=None,
        updated_at=None,
        description=None,
        finding_id=None,
        account_id=None,
        resource_id=None,
        arn=None,
        title=None,
        severity=None,
        confidence=None,
        type=None,
        count=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.detector_id = detector_id
        self.id = finding_id
        self.created_time = created_at
        self.updated_time = updated_at
        self.description = description
        self.type = type
        self.account_id = account_id
        self.resource_id = resource_id
        self.arn = arn
        self.title = title
        self.severity = severity
        self.confidence = confidence
        self.count = count

        try:
            self.created_time_ms = convert_string_to_unix_time(self.created_time)
        except Exception:
            self.created_time_ms = 1

        try:
            self.updated_time_ms = convert_string_to_unix_time(self.updated_time)
        except Exception:
            self.updated_time_ms = 1

    def as_json(self):
        return self.raw_data

    def as_event(self):
        event_data = self.raw_data.copy()
        event_data["detector_id_configured_in_connector_settings"] = self.detector_id
        return dict_to_flat(event_data)

    def as_csv(self):
        return {
            "Finding ID": self.id,
            "Title": self.title,
            "Description": self.description,
            "Type": self.type,
            "Severity": self.severity,
            "Count": self.count,
            "Resource ID": self.resource_id,
            "Created at": self.created_time,
            "Updated at": self.updated_time,
            "Account ID": self.account_id,
        }

    @property
    def siemplify_severity(self):

        if self.severity < 4.0:
            return SEVERITIES["LOW"]

        if self.severity < 7.0:
            return SEVERITIES["MEDIUM"]

        if self.severity < 9.0:
            return SEVERITIES["HIGH"]

        if self.severity <= 10.0:
            return SEVERITIES["CRITICAL"]

        return SEVERITIES["INFORMATIONAL"]

    def as_alert_info(self, environment_common):
        """
        Create an AlertInfo out of the current finding
        :param environment_common: {EnvironmentHandle} The environment common object for fetching the environment
        :return: {AlertInfo} The created AlertInfo object
        """
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.as_event())
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.title
        alert_info.description = self.description
        alert_info.device_vendor = consts.VENDOR
        alert_info.device_product = consts.PRODUCT
        alert_info.priority = self.siemplify_severity
        alert_info.rule_generator = self.type
        alert_info.start_time = self.created_time_ms
        alert_info.end_time = self.updated_time_ms
        alert_info.events = [self.as_event()]
        return alert_info


class IpSet:
    """
    IP Set data model.
    """

    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        format=None,
        location=None,
        status=None,
        tags=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.name = name
        self.format = format
        self.location = location
        self.status = status
        self.tags = tags or []

    def as_json(self):
        return {
            "Format": self.format,
            "Name": self.name,
            "Location": self.location,
            "Status": self.status,
        }

    def as_csv(self):
        return {
            "Name": self.name,
            "Trusted IP List ID": self.id,
            "Location": self.location,
            "Status": self.status,
        }


class TISet:
    """
    Threat Intelligence Set data model.
    """

    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        format=None,
        location=None,
        status=None,
        tags=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.name = name
        self.format = format
        self.location = location
        self.status = status
        self.tags = tags or []

    def as_json(self):
        return {
            "Format": self.format,
            "Name": self.name,
            "Location": self.location,
            "Status": self.status,
        }

    def as_csv(self):
        return {
            "Name": self.name,
            "ID": self.id,
            "Location": self.location,
            "Status": self.status,
        }


class Detector:
    """
    Detector data model.
    """

    def __init__(
        self,
        raw_data,
        id=None,
        created_at=None,
        updated_at=None,
        service_role=None,
        status=None,
        finding_publishing_frequency=None,
        tags=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.created_at = created_at
        self.updated_at = updated_at
        self.service_role = service_role
        self.finding_publishing_frequency = finding_publishing_frequency
        self.status = status
        self.tags = tags or []

    def to_csv(self):
        return {
            "Detector ID": self.id,
            "Status": self.status,
            "Service Role": self.service_role,
            "Created at": self.created_at,
            "Updated at": self.updated_at,
        }

    def to_json(self):
        return {
            "DetectorId": self.id,
            "CreatedAt": self.created_at,
            "ServiceRole": self.service_role,
            "Status": self.status,
            "UpdatedAt": self.updated_at,
        }

    def to_table(self):
        """
        Function that prepares the detector's data to be used on the table
        :return {list} List containing dict of detector's data
        """
        return [self.to_csv()]

from __future__ import annotations
import uuid

from TIPCommon import dict_to_flat
from . import consts
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time

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
        created_at=None,
        updated_at=None,
        description=None,
        category=None,
        finding_id=None,
        account_id=None,
        title=None,
        severity=None,
        score=None,
        type=None,
        count=None,
        archived=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = finding_id
        self.created_time = created_at  # datetime object
        self.updated_time = updated_at  # datetime object
        self.description = description
        self.category = category
        self.type = type
        self.account_id = account_id
        self.title = title
        self.severity = severity
        self.score = score
        self.count = count
        self.archived = archived

        try:
            self.created_time_ms = convert_datetime_to_unix_time(self.created_time)
        except Exception:
            self.created_time_ms = 1

        try:
            self.updated_time_ms = convert_datetime_to_unix_time(self.updated_time)
        except Exception:
            self.updated_time_ms = 1

    def as_json(self):
        return self.raw_data

    def as_event(self):
        return dict_to_flat(self.raw_data)

    def as_csv(self):
        return {
            "Finding ID": self.id,
            "Title": self.title,
            "Category": self.category,
            "Type": self.type,
            "Severity": self.severity,
            "Is Archived": self.archived,
            "Created At": self.created_time,
            "Updated At": self.updated_time,
        }

    @property
    def siemplify_severity(self):
        if str(self.severity).lower() == "low":
            return SEVERITIES["LOW"]
        elif str(self.severity).lower() == "medium":
            return SEVERITIES["MEDIUM"]
        elif str(self.severity).lower() == "high":
            return SEVERITIES["HIGH"]

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
        alert_info.events = [self.as_event()]  # alert <-> event relationship
        return alert_info


class CustomDataIdentifier:
    """
    Amazon Macie Custom Data Identifier
    """

    def __init__(self, raw_data, id):
        self.raw_data = (raw_data,)
        self.id = id

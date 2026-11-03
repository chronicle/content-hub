# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
from collections import OrderedDict
import uuid

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time

from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict
from TIPCommon.types import SingleJson

from microsoft365_defender.core.constants import (
    ADDITIONAL_DATA_ALLOWLIST,
    ALERT_KEYS_TO_IGNORE,
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    ENTITIES_KEY,
    DEVICES_KEY,
    MAX_EVIDENCES_PER_ALERT,
)
from microsoft365_defender.core.Microsoft365DefenderExceptions import Microsoft365DefenderNotImplementedException
from microsoft365_defender.core.UtilsManager import dict_to_md5_hash, severity_to_priority


def _filter_additional_data(alert_data: SingleJson) -> SingleJson:
    """
    Filter additionalData dictionary in alert_data based on ALLOWLIST.

    Args:
        alert_data (SingleJson): Dict representing alert data.

    Returns:
        SingleJson: Alert data with filtered additionalData.
    """
    if "additionalData" in alert_data and isinstance(alert_data["additionalData"], dict):
        alert_data["additionalData"] = {
            k: v for k, v in alert_data["additionalData"].items()
            if k in ADDITIONAL_DATA_ALLOWLIST
        }
        if not alert_data["additionalData"]:
            alert_data.pop("additionalData", None)
    else:
        alert_data.pop("additionalData", None)
    return alert_data


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Device(BaseModel):
    def __init__(self, raw_data):
        super(Device, self).__init__(raw_data)


class BaseAlert(BaseModel):
    def __init__(
        self,
        raw_data,
        alert_id,
        incident_id,
        title,
        severity,
        assignee,
        first_activity,
        last_activity,
        description,
    ):
        super(BaseAlert, self).__init__(raw_data)
        self.alert_id = alert_id
        self.incident_id = incident_id
        self.title = title
        self.severity = severity
        self.assignee = assignee
        self.first_activity = first_activity
        self.last_activity = last_activity
        self.description = description
        self.alert_unique_id = alert_id

    def get_alert_info(
        self,
        alert_info,
        environment_common,
        incident_event,
        is_tracking_enabled=False
    ):
        """
        Build alert info object

        Args:
            alert_info (AlertInfo): AlertInfo object
            environment_common (EnvironmentHandle): EnvironmentHandle object
            incident_event (dict[str, str]): flat dict of incident event
            is_tracking_enabled (bool): specifies if alerts tracking is enabled

        Returns:
            AlertInfo: AlertInfo object
        """
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.incident_id
        alert_info.display_id = (
            self.alert_unique_id if is_tracking_enabled else self.alert_id
        )
        alert_info.name = self.title
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = self.title
        alert_info.source_grouping_identifier = self.incident_id
        alert_info.start_time = convert_string_to_unix_time(self.first_activity)
        alert_info.end_time = convert_string_to_unix_time(self.last_activity)
        alert_info.events = self.create_events(incident_event)

        return alert_info

    def get_severity(self):
        return severity_to_priority(self.severity)

    def create_events(self, incident_event):
        raise Microsoft365DefenderNotImplementedException

    def to_hash(self):
        raise Microsoft365DefenderNotImplementedException


class Alert(BaseAlert):
    def __init__(
        self,
        raw_data,
        alert_id,
        incident_id,
        title,
        severity,
        first_activity,
        last_activity,
        description,
        entities,
        devices,
    ):
        super(Alert, self).__init__(
            raw_data=raw_data,
            alert_id=alert_id,
            incident_id=incident_id,
            title=title,
            severity=severity,
            first_activity=first_activity,
            last_activity=last_activity,
            description=description,
        )
        self.entities = entities
        self.devices = devices
        self.alert_unique_id = f"{alert_id}_{self.to_hash()}"

    def create_events(self, incident_event):
        events = [incident_event]
        alert_data = copy.deepcopy(self.to_json())
        _filter_additional_data(alert_data)
        alert_data["event_type"] = "Alert"
        entites = alert_data.pop(ENTITIES_KEY, None) or []
        devices = alert_data.pop(DEVICES_KEY, None) or []
        if len(entites) >= len(devices):
            for i, entity in enumerate(entites):
                if isinstance(entity, dict):
                    entity = copy.deepcopy(entity)
                    entity.pop("additionalData", None)
                alert_data[ENTITIES_KEY] = entity
                device = (
                    devices[i] if i < len(devices) else devices[0] if devices else None
                )
                if device:
                    if isinstance(device, dict):
                        device = copy.deepcopy(device)
                        device.pop("additionalData", None)
                    alert_data[DEVICES_KEY] = device
                events.append(dict_to_flat(alert_data))
        elif len(entites) < len(devices):
            for i, device in enumerate(devices):
                if isinstance(device, dict):
                    device = copy.deepcopy(device)
                    device.pop("additionalData", None)
                alert_data[DEVICES_KEY] = device
                entity = (
                    entites[i] if i < len(entites) else entites[0] if entites else None
                )
                if entity:
                    if isinstance(entity, dict):
                        entity = copy.deepcopy(entity)
                        entity.pop("additionalData", None)
                    alert_data[ENTITIES_KEY] = entity
                events.append(dict_to_flat(alert_data))

        return events

    def to_hash(self):
        return dict_to_md5_hash(
            OrderedDict(sorted(self.raw_data.items())), ALERT_KEYS_TO_IGNORE
        )

class AlertComment(BaseModel):
    def __init__(
        self,
        raw_data: SingleJson,
        comment: str,
        created_time: str,
    ) -> None:
        super().__init__(raw_data)
        self.comment = comment
        self.created_time = created_time

    @classmethod
    def from_json(cls, comment_data: SingleJson) -> "AlertComment":
        return cls(
            raw_data=comment_data,
            comment=comment_data.get("comment"),
            created_time=comment_data.get("createdDateTime"),
        )

class AlertWithEvidence(BaseAlert):
    def __init__(
        self,
        raw_data,
        alert_id,
        incident_id,
        title,
        severity,
        assignee,
        first_activity,
        last_activity,
        description,
        evidences,
    ):
        super(AlertWithEvidence, self).__init__(
            raw_data=raw_data,
            alert_id=alert_id,
            incident_id=incident_id,
            title=title,
            severity=severity,
            assignee=assignee,
            first_activity=first_activity,
            last_activity=last_activity,
            description=description,
        )
        self.comments: list[AlertComment] = []
        self.evidences = evidences
        self.alert_unique_id = f"{alert_id}_{self.to_hash()}"

    def create_events(self, incident_event):
        events = [incident_event]
        alert_data = copy.deepcopy(self.to_json())
        _filter_additional_data(alert_data)

        alert_event_data = copy.deepcopy(alert_data)
        alert_event_data["event_type"] = "Alert"
        if "kind" not in alert_event_data:
            alert_event_data["kind"] = "Alert"
        if "@odata.type" not in alert_event_data:
            alert_event_data["@odata.type"] = "Alert"
        if "name" not in alert_event_data:
            alert_event_data["name"] = self.title or alert_event_data.get("title", "")
        if "type" not in alert_event_data:
            alert_event_data["type"] = "Alert"
        events.append(dict_to_flat(alert_event_data))

        sorted_evidences = sorted(
            self.evidences,
            key=lambda e: (
                e.get("createdDateTime")
                or e.get("evidenceCreationTime")
                or e.get("firstSeenDateTime")
                or ""
            ),
        )
        latest_evidences = sorted_evidences[-MAX_EVIDENCES_PER_ALERT:]

        alert_metadata = copy.deepcopy(alert_data)
        alert_metadata.pop("evidence", None)
        alert_metadata.pop("evidences", None)
        alert_metadata.pop("assets", None)

        for evidence_data in latest_evidences:
            evidence_copy = copy.deepcopy(evidence_data)
            evidence_copy.pop("additionalData", None)
            evidence_copy["event_type"] = "Evidence"
            evidence_copy["alert_metadata"] = alert_metadata
            events.append(dict_to_flat(evidence_copy))

        return events

    def to_hash(self):
        evidences = [
            dict_to_md5_hash(
                OrderedDict(sorted(evidence.items())), ALERT_KEYS_TO_IGNORE
            ) for evidence in self.evidences
        ]
        evidences.sort()

        raw_data_copy = copy.deepcopy(self.raw_data)
        raw_data_copy.pop("evidence", None)
        raw_data_copy.pop("evidences", None)
        raw_data_copy.pop("assets", None)

        return dict_to_md5_hash(
            OrderedDict(sorted({
                **raw_data_copy,
                "evidence": evidences
            }.items())), ALERT_KEYS_TO_IGNORE
        )

    def add_comments(self, comments: list[AlertComment]):
        self.comments.extend(
            comments
        )

class Incident(BaseModel):
    def __init__(
        self,
        raw_data,
        incident_id,
        incident_name,
        severity,
        classification,
        created_time,
        last_update_time,
        alerts,
    ):
        super(Incident, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.incident_id = incident_id
        self.incident_name = incident_name
        self.severity = severity
        self.classification = classification
        self.created_time = created_time
        self.last_update_time = last_update_time
        self.alerts = alerts

    def get_alert_info(self, alert_info, environment_common):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.incident_id
        alert_info.display_id = self.incident_id
        alert_info.name = self.incident_name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = self.incident_name
        alert_info.source_grouping_identifier = self.incident_id
        alert_info.end_time = alert_info.start_time = convert_string_to_unix_time(
            self.created_time
        )
        alert_info.events = [self.as_event()]

        return alert_info

    def get_severity(self):
        return severity_to_priority(self.severity)

    def as_event(self):
        event_data = copy.deepcopy(self.raw_data)
        event_data.pop("alerts", None)
        event_data.pop("additionalData", None)
        event_data["event_type"] = "Incident"
        if "kind" not in event_data:
            event_data["kind"] = "Incident"
        if "@odata.type" not in event_data:
            event_data["@odata.type"] = "Incident"
        if "name" not in event_data:
            event_data["name"] = self.incident_name or event_data.get("displayName", "")
        if "type" not in event_data:
            event_data["type"] = "Incident"
        return dict_to_flat(event_data)

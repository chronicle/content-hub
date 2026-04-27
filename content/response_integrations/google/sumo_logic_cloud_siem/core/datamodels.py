from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
import uuid
import copy
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    DISPLAY_ID_PREFIX,
    SUMOLOGIC_SEVERITY_MAPPING,
    TACTIC_TAG_PREFIX,
    TECHNIQUE_TAG_PREFIX,
)
from .UtilsManager import convert_list_to_comma_string


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Insight(BaseModel):
    def __init__(self, raw_data, id, readable_id, name, description, severity, created):
        super(Insight, self).__init__(raw_data)
        self.uuid = str(uuid.uuid4())
        self.id = id
        self.readable_id = readable_id
        self.name = name
        self.description = description
        self.severity = severity
        self.created = created

        try:
            self.timestamp_ms = convert_string_to_unix_time(self.created + "Z")
        except Exception:
            self.timestamp_ms = 1

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = f"{DISPLAY_ID_PREFIX}{self.id}"
        alert_info.name = f"{self.readable_id}: {self.name}"
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = self.name
        alert_info.source_grouping_identifier = self.name
        alert_info.end_time = alert_info.start_time = self.timestamp_ms
        alert_info.extensions = self.to_extensions()
        alert_info.events = self.to_events()

        return alert_info

    def get_severity(self):
        return SUMOLOGIC_SEVERITY_MAPPING.get(self.severity, -1)

    def to_extensions(self):
        extension_data = copy.deepcopy(self.raw_data)
        extension_data.pop("artifacts", None)
        extension_data.pop("signals", None)
        return dict_to_flat(extension_data)

    def to_events(self):
        events = []
        signals = copy.deepcopy(self.raw_data.get("signals", []))
        for signal in signals:
            all_records = signal.pop("allRecords", None)
            mitre_data = []
            for tag in signal.get("tags", []):
                if TACTIC_TAG_PREFIX in tag:
                    mitre_data.append(tag.replace(TACTIC_TAG_PREFIX, ""))
                elif TECHNIQUE_TAG_PREFIX in tag:
                    mitre_data.append(tag.replace(TECHNIQUE_TAG_PREFIX, ""))
            signal["mitre_data"] = mitre_data
            for record in all_records:
                event_data = copy.deepcopy(record)
                event_data["generalized_data"] = signal
                events.append(dict_to_flat(event_data))

        return events

    def to_json(self):
        data = copy.deepcopy(self.raw_data)
        data.get("data", {}).pop("signals", None)
        return data


class EntityInfo(BaseModel):
    def __init__(
        self,
        raw_data,
        name,
        is_suppressed,
        is_whitelisted,
        tags,
        first_seen,
        last_seen,
        criticality,
        activity_score,
    ):
        super(EntityInfo, self).__init__(raw_data)
        self.name = name
        self.is_suppressed = is_suppressed
        self.is_whitelisted = is_whitelisted
        self.tags = tags
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.criticality = criticality
        self.activity_score = activity_score

    def to_enrichment_data(self, prefix=None):
        data = {
            "isSuppressed": self.is_suppressed,
            "isWhitelisted": self.is_whitelisted,
            "tags": convert_list_to_comma_string(self.tags),
            "firstSeen": self.first_seen,
            "lastSeen": self.last_seen,
            "criticality": self.criticality,
            "activityScore": self.activity_score,
        }

        data = dict_to_flat(
            {key: value for key, value in data.items() if value is not None}
        )
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self):
        return (
            f"<h2>"
            f"<strong>"
            f'Activity Score: {self.activity_score or "N/A"} '
            f'Criticality: {self.criticality or "N/A"}'
            f"</strong>"
            f"</h2>"
            f"<p>"
            f'<strong>Name: </strong>{self.name or "N/A"}'
            f'<strong><br />Tags: </strong>{convert_list_to_comma_string(self.tags) or "N/A"}<br />'
            f'<strong>First Seen:</strong> {self.first_seen or "N/A"}<br />'
            f'<strong>Last Seen:</strong> {self.last_seen or "N/A"}<br />'
            f'<strong>Suppressed:</strong> {self.is_suppressed if self.is_suppressed is not None else "N/A"}'
            f"</p>"
            f"<p>&nbsp;</p>"
        )


class Signal(BaseModel):
    def __init__(self, raw_data):
        super(Signal, self).__init__(raw_data)

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

import re
import isodate
from enum import Enum

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon.transformation import dict_to_flat, flat_dict_to_csv

from .constants import ALERT_TYPES_WITH_EVENTS
from .utils import convert_list_to_comma_string, handle_special_characters


EPOCH_DATETIME = "1970-01-01T00:00:00.000Z"


KIND_TO_VALUE_MAPPING = {
    "Account": "account_name",
    "Host": "host_name",
    "Ip": "address",
    "Mailbox": "mailbox_primary_address",
}


class SentinelPriorityEnum(Enum):
    DRAFT = "Draft"
    INFO = "Informational"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class SiemplifyPriorityEnum(Enum):
    INFO = -1
    DRAFT = -1
    LOW = 40
    MEDIUM = 60
    HIGH = 80
    CRITICAL = 100


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def is_empty(self):
        return not bool(self.raw_data)


class AggregationBySeverity:
    # In this case we are using CamelCase because API sends it in CamelCase
    def __init__(
        self,
        totalCriticalSeverity=None,
        totalHighSeverity=None,
        totalMediumSeverity=None,
        totalLowSeverity=None,
        totalInformationalSeverity=None,
        **kwargs,
    ):
        self.total_critical_severity = totalCriticalSeverity
        self.total_high_severity = totalHighSeverity
        self.total_medium_severity = totalMediumSeverity
        self.total_low_severity = totalLowSeverity
        self.total_informational_severity = totalInformationalSeverity

    def to_json(self):
        return {
            "Total_Critical_Severity": self.total_critical_severity,
            "Total_High_Severity": self.total_high_severity,
            "Total_Medium_Severity": self.total_medium_severity,
            "Total_Low_Severity": self.total_low_severity,
            "Total_Informational_Severity": self.total_informational_severity,
        }

    def to_csv(self):
        return {
            "Critical": self.total_critical_severity,
            "High": self.total_high_severity,
            "Medium": self.total_medium_severity,
            "Low": self.total_low_severity,
            "Informational": self.total_informational_severity,
        }


class AggregationByStatus:
    # In this case we are using CamelCase because API sends it in CamelCase
    def __init__(
        self,
        totalNewStatus=None,
        totalInProgressStatus=None,
        totalResolvedStatus=None,
        totalDismissedStatus=None,
        totalTruePositiveStatus=None,
        totalFalsePositiveStatus=None,
        **kwargs,
    ):
        self.total_new_status = totalNewStatus
        self.total_in_progress_status = totalInProgressStatus
        self.total_resolved_status = totalResolvedStatus
        self.total_dismissed_status = totalDismissedStatus
        self.total_true_positive_status = totalTruePositiveStatus
        self.total_false_positive_status = totalFalsePositiveStatus

    def to_json(self):
        return {
            "Total_New_Status": self.total_new_status,
            "Total_In_Progress_Status": self.total_in_progress_status,
            "Total_Resolved_Status": self.total_resolved_status,
            "Total_Dismissed_Status": self.total_dismissed_status,
            "Total_True_Positive_Status": self.total_true_positive_status,
            "Total_False_Positive_Status": self.total_false_positive_status,
        }

    def to_csv(self):
        return {
            "New": self.total_new_status,
            "In Progress": self.total_in_progress_status,
            "Resolved": self.total_resolved_status,
            "Dismissed": self.total_dismissed_status,
            "True Positive": self.total_true_positive_status,
            "False Positive": self.total_false_positive_status,
        }


class IncidentProperties:
    # In this case we are using CamelCase because API sends it in CamelCase
    def __init__(
        self,
        title=None,
        description=None,
        status=None,
        severity=None,
        labels=None,
        owner=None,
        metrics=None,
        classification=None,
        **kwargs,
    ):
        self.title = title
        self.description = description
        self.status = status
        self.severity = severity
        self.assigned_to = kwargs.get("assignedTo")
        self.close_reason = kwargs.get("closeReason")
        self.case_number = kwargs.get("caseNumber")
        self.incident_number = kwargs.get("incidentNumber")
        self.incident_url = kwargs.get("incidentUrl")
        self.labels = self.get_labels(labels or [])
        self.related_alert_ids = kwargs.get("relatedAlertIds")
        self.created_time_utc = kwargs.get("createdTimeUtc")
        self.created_time_unix = (
            convert_string_to_unix_time(self.created_time_utc)
            if self.created_time_utc
            else 0
        )
        self.first_alert_time_generated = kwargs.get(
            "firstAlertTimeGenerated", EPOCH_DATETIME
        )
        self.last_alert_time_generated = kwargs.get(
            "lastAlertTimeGenerated", EPOCH_DATETIME
        )
        self.first_activity_time_generated = kwargs.get("firstActivityTimeGenerated")
        self.last_activity_time_generated = kwargs.get("lastActivityTimeGenerated")
        self.last_updated_time_utc = kwargs.get("lastUpdatedTimeUtc")
        self.last_modified_time_utc = kwargs.get("lastModifiedTimeUtc")
        self.alert_product_names = kwargs.get("alertProductNames")
        self.start_time_utc = kwargs.get("startTimeUtc")
        self.end_time_utc = kwargs.get("endTimeUtc")
        self.owner = Owner(owner, **owner) if owner else None
        self.total_comments = kwargs.get("totalComments")
        self.metrics = metrics
        self.system_alert_id = kwargs.get("systemAlertId")
        self.provider_incident_id = kwargs.get("providerIncidentId")
        self.additional_data = kwargs.get("additionalData")
        self.product_component_name = kwargs.get("productComponentName")
        self.vendor_name = kwargs.get("vendorName")
        self.product_name = kwargs.get("productName")
        self.provider_name = kwargs.get("providerName")
        self.has_labels = bool(labels)
        self.alerts: list[IncidentAlert] = []
        self.classification = classification
        self.classificationReason = kwargs.get("classificationReason")
        self.classificationComment = kwargs.get("classificationComment")

    def get_labels(self, labels):
        return (
            [Label(**label) for label in labels]
            if labels and isinstance(labels[0], dict)
            else [Label(labelName=label) for label in labels]
        )

    def to_json(self):
        return {
            "Title": self.title,
            "Description": self.description,
            "Status": self.status,
            "Assigned_To": self.owner.assigned_to,
            "Severity": self.severity,
            "Close_Reason": (
                f"{self.classification}-{self.classificationReason}"
                if self.classificationReason
                else self.classification
            ),
            "Closing_Comment": self.classificationComment,
            "Case_Number": self.case_number,
            "Labels": self.labels,
            "Created_Time_UTC": self.created_time_utc,
            "First_Alert_Time_Generated": self.first_alert_time_generated,
            "Last_Alert_Time_Generated": self.last_alert_time_generated,
            "Last_Updated_Time_UTC": self.last_updated_time_utc,
            "Alert_Product_Names": self.alert_product_names,
            "Start_Time_UTC": self.start_time_utc,
            "End_Time_UTC": self.end_time_utc,
            "Owner": self.owner.to_json(),
            "Total_Comments": self.total_comments,
            "Metrics": self.metrics,
            "Alerts": self.alerts,
        }

    def to_csv(self):
        return {
            "Incident Number": self.incident_number,
            "Title": self.title,
            "Description": self.description,
            "Severity": self.severity,
            "Status": self.status,
            "Labels": self.labels_to_csv(),
            "Assigned To": self.owner.assigned_to,
            "Alert Product Names": convert_list_to_comma_string(
                self.alert_product_names, delimiter="; "
            ),
            "Created Time UTC": self.created_time_utc,
            "Last Update Time UTC": self.last_updated_time_utc,
        }

    def labels_to_csv(self):
        return convert_list_to_comma_string(
            [str(label) for label in self.labels], delimiter="; "
        )


class Owner(BaseModel):
    # In this case we are using CamelCase because API sends it in CamelCase
    def __init__(self, raw_data, assignedTo=None, **kwargs):
        super().__init__(raw_data)
        self.assigned_to = assignedTo


class Label:
    def __init__(self, labelName, **kwargs):
        self.name = labelName

    def __str__(self):
        return str(self.name)


class IncidentStatisticProperties:
    # In this case we are using CamelCase because API sends it in CamelCase
    def __init__(self, aggregationBySeverity=None, aggregationByStatus=None, **kwargs):
        self.aggregation_by_severity = (
            AggregationBySeverity(**aggregationBySeverity)
            if aggregationBySeverity
            else None
        )
        self.aggregation_by_status = (
            AggregationByStatus(**aggregationByStatus) if aggregationByStatus else None
        )

    def to_json(self):
        return {
            "Aggregation_By_Severity": (
                self.aggregation_by_severity.to_json()
                if self.aggregation_by_severity
                else None
            ),
            "Aggregation_By_Status": (
                self.aggregation_by_status.to_json()
                if self.aggregation_by_status
                else None
            ),
        }


class Incident(BaseModel):
    def __init__(
        self,
        raw_data: dict,
        id_: str = None,
        name: str = None,
        etag: str = None,
        type_: str = None,
        incident_properties: IncidentProperties = None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = id_
        self.name = name
        self.etag = etag
        self.type = type_
        self.properties = incident_properties
        self.has_properties = bool(incident_properties)
        self.incident_number = (
            self.properties.incident_number if self.has_properties else None
        )
        self.labels = [
            str(label) for label in self.properties.labels if self.has_properties
        ]

        # Connector ingestion ID
        self.alert_id = self.name
        # Ingestion status
        self.fully_fetched = True
        self.comments = []
        self.alerts = []

    def is_scheduled_or_nrt(self):
        return bool(
            len(self.properties.alerts) > 0
            and all(a.is_scheduled_or_nrt() for a in self.properties.alerts)
        )

    @property
    def incident_title(self) -> str:
        """Get incident title out of 'properties.title', handle special characters."""
        title = " ".join(self.properties.title.split()) if self.properties.title else ""
        return handle_special_characters(title)

    @property
    def incident_labels(self) -> list[str]:
        """Get incident labels out of 'properties.labels.labelName'."""
        return [label.name for label in self.properties.labels]

    @property
    def incident_alerts(self) -> list[IncidentAlert]:
        """Get incident properties alerts"""
        return (self.properties and self.properties.alerts) or []

    @property
    def created_time_ts(self) -> int:
        """Extract created time from properties and returns it as timestamp."""
        created_time_utc = getattr(self.properties, "created_time_utc", None)
        return (
            convert_string_to_unix_time(created_time_utc)
            if created_time_utc is not None
            else 0
        )

    @property
    def last_modified_time_ts(self) -> int:
        """Extract last modified time from properties and returns it as timestamp."""
        last_modified_time_utc = getattr(
            self.properties, "last_modified_time_utc", None
        )
        return (
            convert_string_to_unix_time(last_modified_time_utc)
            if last_modified_time_utc is not None
            else 0
        )

    def to_csv(self):
        result = {"Incident ID": self.name}

        if self.has_properties:
            result.update(self.properties.to_csv())

        return dict_to_flat(result)

    def to_event(self):
        return self.raw_data

    def raw_to_flat_data(self):
        return dict_to_flat(self.raw_data)

    def get_original_data(self):
        return self.raw_data

    def update_labels(self, labels=None):
        data = self.get_original_data()
        if not labels:
            return data, None, None

        incident_labels = [label["labelName"] for label in data["properties"]["labels"]]
        already_existing_labels = [
            label for label in labels if label in incident_labels
        ]
        updating_labels = [label for label in labels if label not in incident_labels]
        data["properties"]["labels"] += [
            {"labelName": item, "labelType": "User"} for item in updating_labels
        ]

        return data, updating_labels, already_existing_labels

    def add_comments(self, comments: list[IncidentComment]):
        self.comments.extend(
            filter(lambda comment: self.name in comment.comment_id, comments)
        )

    def add_alerts(self, alerts: list[IncidentAlert]):
        self.alerts.extend(
            filter(lambda alert: self.name in alert.incident_name, alerts)
        )


class IncidentComment(BaseModel):
    def __init__(
        self,
        raw_data,
        comment_id,
        name,
        etag,
        type_,
        properties,
        message,
        created_time,
        modified_time,
        author,
    ):
        super().__init__(raw_data)
        self.name = name
        self.comment_id = comment_id
        self.etag = etag
        self.type = type_
        self.properties = properties
        self.message = message
        self.created_time = created_time
        self.modified_time = modified_time
        self.author = author

    @classmethod
    def from_json(cls, comment_data):
        properties = comment_data.get("properties")
        return cls(
            raw_data=comment_data,
            comment_id=comment_data.get("id"),
            name=comment_data.get("name"),
            etag=comment_data.get("etag"),
            type_=comment_data.get("type"),
            properties=properties,
            message=properties.get("message"),
            created_time=properties.get("createdTimeUtc"),
            modified_time=properties.get("lastModifiedTimeUtc"),
            author=properties.get("author"),
        )


class IncidentStatistic(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        kind=None,
        type=None,
        properties=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = id
        self.name = name
        self.kind = kind
        self.type = type
        self.properties = (
            IncidentStatisticProperties(**properties) if properties else None
        )
        self.has_properties = bool(properties)

    def to_json(self):
        return {
            "ID": self.id,
            "Name": self.name,
            "Kind": self.kind,
            "Type": self.type,
            "Properties": self.properties.to_json() if self.has_properties else None,
        }


class IncidentAlert(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        kind=None,
        type=None,
        properties=None,
        entities=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = id
        self.name = name
        self.kind = kind
        self.type = type
        self.entities = entities
        self.properties = IncidentProperties(**properties) if properties else None

        self.fully_fetched = False
        self.scheduled_alert: ScheduledAlert | None = None
        self.incident_name = kwargs.get("incidentName", "")

    def to_json(self):
        return self.raw_data

    def is_scheduled_or_nrt(self) -> bool:
        return self.properties.product_component_name in ALERT_TYPES_WITH_EVENTS

    def to_event(self):
        if self.scheduled_alert is not None:
            return self.scheduled_alert.to_event()

        self.raw_data["entities"] = [entity.to_json() for entity in self.entities or []]
        return dict_to_flat(self.raw_data)

    def to_enrichment_data(self):
        pass


class ScheduledAlert(BaseModel):
    """Data model for Scheduled or NRT alert, that's build out of Query Result."""

    def __init__(
        self,
        raw_data: dict,
        system_alert_id: str,
        product_component_name: str,
        vendor_name: str,
    ):
        super().__init__(raw_data)
        self.system_alert_id = system_alert_id
        self.product_component_name = product_component_name
        self.vendor_name = vendor_name

        self.events = []

    def get_events_flat(self):
        return list(map(dict_to_flat, self.events))

    def to_event(self):
        """Build flat event dict out of ScheduledAlert data model."""
        self.raw_data["events"] = self.get_events_flat()
        return dict_to_flat(self.raw_data)


class AlertEntity(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        kind=None,
        type=None,
        properties=None,
        additional_data=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = id
        self.name = name
        self.kind = kind
        self.type = type
        self.additional_data = additional_data if additional_data else {}
        self.properties = (
            AlertEntityProperties(raw_data=properties, **properties)
            if properties
            else None
        )

    def to_json(self):
        self.raw_data["additionalData"] = self.additional_data
        return self.raw_data

    def get_value(self):
        return getattr(self.properties, KIND_TO_VALUE_MAPPING.get(self.kind, ""), "")

    def to_enrichment_data(self):
        pass


class AlertEntityProperties(BaseModel):
    def __init__(
        self,
        raw_data,
        hostName=None,
        accountName=None,
        address=None,
        mailboxPrimaryAddress=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.host_name = hostName
        self.account_name = accountName
        self.address = address
        self.mailbox_primary_address = mailboxPrimaryAddress

    def to_enrichment_data(self):
        pass

    def to_json(self):
        return self.raw_data


class AlertRuleProperties(BaseModel):
    # In this case we are using CamelCase because API sends it in CamelCase
    def __init__(
        self,
        alertRuleTemplateName=None,
        description=None,
        displayName=None,
        enabled=None,
        lastModifiedUtc=None,
        query=None,
        queryFrequency=None,
        queryPeriod=None,
        severity=None,
        suppressionDuration=None,
        suppressionEnabled=None,
        tactics=None,
        triggerOperator=None,
        triggerThreshold=None,
        **kwargs,
    ):
        self.alert_rule_template_name = alertRuleTemplateName
        self.description = description
        self.display_name = displayName
        self.enabled = enabled
        self.last_modified_utc = lastModifiedUtc
        self.query = query
        self.query_frequency = queryFrequency
        self.query_period = queryPeriod
        self.severity = severity
        self.suppression_duration = suppressionDuration
        self.suppression_enabled = suppressionEnabled
        self.tactics = tactics
        self.trigger_operator = triggerOperator
        self.trigger_threshold = triggerThreshold

    def to_json(self):
        return {
            "Alert_Rule_Template_Name": self.alert_rule_template_name,
            "Description": self.description,
            "Display_Name": self.display_name,
            "Enabled": self.enabled,
            "Last_Modified_UTC": self.last_modified_utc,
            "Query": self.query,
            "Query_Frequency": self.parse_iso8601_time(self.query_frequency),
            "Query_Period": self.parse_iso8601_time(self.query_period),
            "Severity": self.severity,
            "Suppression_Duration": self.parse_iso8601_time(self.suppression_duration),
            "Suppression_Enabled": self.suppression_enabled,
            "Tactics": self.tactics,
            "Trigger": self.trigger,
        }

    @staticmethod
    def parse_iso8601_time(time):
        if not time:
            return None

        time_delta = isodate.parse_duration(time)
        days, seconds = time_delta.days, time_delta.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return (
            f"{days} {'day' if days == 1 else 'days'} {hours} "
            f"{'hour' if hours == 1 else 'hours'} {minutes} "
            f"{'minute' if minutes == 1 else 'minutes'} {seconds} "
            f"{'second' if seconds == 1 else 'seconds'}"
        )

    @property
    def trigger(self):
        return (
            "{} {}".format(
                re.sub(r"(?<=\w)([A-Z])", r" \1", self.trigger_operator),
                self.trigger_threshold,
            )
            if self.trigger_operator and self.trigger_threshold
            else None
        )

    def to_table(self):
        return {
            "Name": self.display_name,
            "Enabled": self.enabled,
            "Description": self.description,
            "Query": self.query,
            "Query Period": self.parse_iso8601_time(self.query_period),
            "Frequency": self.parse_iso8601_time(self.query_frequency),
            "Trigger": self.trigger,
            "Tactics": convert_list_to_comma_string(self.tactics, delimiter="; "),
            "Enable Suppression": self.suppression_enabled,
            "Suppression Duration": self.parse_iso8601_time(self.suppression_duration),
            "Last Modification Time": self.last_modified_utc,
        }


class AlertRule(BaseModel):
    def __init__(
        self,
        raw_data,
        etag=None,
        id=None,
        kind=None,
        name=None,
        type=None,
        properties=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.etag = etag
        self.name = name
        self.id = id
        self.kind = kind
        self.type = type
        self.properties = AlertRuleProperties(**properties) if properties else None

    def to_json(self):
        return {
            "ID": self.id,
            "ETag": self.etag,
            "Name": self.name,
            "Kind": self.kind,
            "Type": self.type,
            "Properties": self.properties.to_json() if self.properties else None,
        }

    def to_table(self):
        result = {"Alert ID": self.name}

        if self.properties:
            result.update(self.properties.to_table())

        return result

    def get_original_data(self):
        return self.raw_data


class TagCollection:
    def __init__(self, tags=None):
        self.raw_data = tags or []
        self.tags = [Tag(**tag) for tag in self.raw_data]

    def __contains__(self, value):
        for tag in self.tags:
            if value in tag:
                return True

        return False

    def filter_by_name(self, name):
        return [tag.value for tag in self.tags if tag.name == name]

    def find_by_name(self, name):
        for tag in self.tags:
            if tag.name == name:
                return tag.value

    def to_json(self):
        return [tag.to_json() for tag in self.tags]

    def set(self, name, value):
        self.tags.append(Tag(name, value))

    def remove_all(self, name):
        self.tags = [tag for tag in self.tags if tag.name != name]

    def set_from_list(self, name, values):
        for value in values:
            self.set(name, value)

    def set_from_list_unique_values(self, name, values, unique_tag_name=None):
        for value in values:
            if (unique_tag_name, value) in self:
                continue

            self.set(name, value)


class Tag:
    # In this case we are using CamelCase because API sends it in CamelCase
    def __init__(self, Name=None, Value=None, **kwargs):
        self.name = Name
        self.value = Value

    def __contains__(self, field):
        name, value = field if isinstance(field, tuple) else (None, field)
        return value in self.value and name == self.name if name else True

    def to_json(self):
        return {"Name": self.name, "Value": self.value}


class CustomHuntingRuleProperties(BaseModel):
    # In this case we are using CamelCase because API sends it in CamelCase
    def __init__(
        self,
        raw_data,
        Category=None,
        DisplayName=None,
        Query=None,
        Tags=None,
        Version=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.category = Category
        self.display_name = DisplayName
        self.query = Query
        self.tags = TagCollection(Tags or [])
        self.version = Version

    def to_json(self):
        return {
            "Category": self.category,
            "Display_Name": self.display_name,
            "Query": self.query,
            "Tags": self.tags.to_json(),
            "Version": self.version,
            "Tactics": self.tactics,
        }

    @property
    def tactics(self):
        return self.tags.filter_by_name("tactics")

    @property
    def description(self):
        return self.tags.find_by_name("description")

    @property
    def created_time_utc(self):
        return self.tags.find_by_name("createdTimeUtc")

    def to_csv(self):
        return {
            "Title": self.display_name,
            "Category": self.category,
            "Description": self.description,
            "Tactics": convert_list_to_comma_string(self.tactics, delimiter="; "),
            "Query": self.query,
            "Created Time UTC": self.created_time_utc,
        }


class CustomHuntingRulePropertiesRequest(CustomHuntingRuleProperties):
    def __init__(self, raw_data):
        super().__init__(raw_data, **raw_data)

    def to_create_json(self):
        return {
            "Category": self.category or "General Exploration",
            "DisplayName": self.display_name,
            "Query": self.query,
            "Tags": self.tags.to_json(),
            "Tactics": self.tactics,
        }

    def to_update_json(self):
        return {k: v for k, v in self.to_create_json().items() if v is not None}


class CustomHuntingRule(BaseModel):
    def __init__(
        self, raw_data, etag=None, id=None, name=None, properties=None, **kwargs
    ):
        properties = properties or {}
        super().__init__(raw_data)
        self.id = id
        self.etag = etag
        self.name = self.get_name(name)
        self.has_properties = bool(properties)
        self.properties = CustomHuntingRuleProperties(properties, **properties)

    def __str__(self):
        return self.name

    def get_name(self, name):
        return name if name else self.id.split("/")[-1] if self.id else None

    def to_json(self):
        return {
            "ID": self.id,
            "ETag": self.etag,
            "Name": self.name,
            "Properties": self.properties.to_json() if self.has_properties else None,
        }

    def to_csv(self):
        result = {"Hunting Rule ID": self.name}

        if self.has_properties:
            result.update(self.properties.to_csv())

        return result

    def to_table(self):
        return flat_dict_to_csv(self.to_csv())


class CustomHuntingRuleRequest(CustomHuntingRule):
    def __init__(self, raw_data=None, properties=None, **kwargs):
        raw_data = raw_data or {}
        properties = properties or {}
        super().__init__(raw_data, **kwargs)
        self.properties = CustomHuntingRulePropertiesRequest(properties)

    def to_create_json(self):
        return {"properties": self.properties.to_create_json()}

    def to_update_json(self):
        return {**self.raw_data, "properties": self.properties.to_update_json()}


class Column(BaseModel):
    def __init__(self, raw_data, name, **kwargs):
        super().__init__(raw_data)
        self.name = name


class PrimaryResult(BaseModel):
    def __init__(self, name=None, rows=None, columns=None, **kwargs):
        self.name = name
        self.rows = rows or []
        self.columns = [Column(column, **column) for column in columns or []]
        super().__init__(
            [
                {
                    column.name: column_value
                    for column, column_value in zip(self.columns, row)
                }
                for row in self.rows
            ]
        )

    def to_csv(self, include_empty_tactics=False):
        csv_result = []
        for result in map(dict.copy, self.to_json()):
            tactics = result.get("Tactics")
            if not tactics:
                if include_empty_tactics:
                    csv_result.append(dict_to_flat(result))
                continue

            result["Tactics"] = convert_list_to_comma_string(
                tactics.split(","), delimiter="; "
            )
            csv_result.append(dict_to_flat(result))

        return csv_result

    def to_table(self, include_empty_tactics=False):
        return self.to_csv(include_empty_tactics)

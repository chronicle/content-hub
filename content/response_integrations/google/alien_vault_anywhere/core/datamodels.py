from __future__ import annotations
from enum import Enum


class SiemplifyPriorityEnum(Enum):
    INFO = -1
    LOW = 40
    MEDIUM = 60
    HIGH = 80


class AlienVaultAlarmModel:
    def __init__(
        self,
        raw_data,
        name,
        timestamp,
        priority,
        uuid,
        original_priority=None,
        events=[],
        timestamp_received=None,
        source_name=None,
        rule_id=None,
        rule_intent=None,
        priority_label=None,
        timestamp_occured_iso8601=None,
        timestamp_received_iso8601=None,
        rule_attack_tactic=None,
        rule_strategy=None,
        rule_attack_technique=None,
        rule_attack_id=None,
        source_organisation=None,
        source_country=None,
        destination_name=None,
        is_suppressed=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.uuid = uuid
        self.name = name
        self.timestamp = timestamp
        self.timestamp_received = timestamp_received
        self.priority = priority
        self.original_priority = original_priority
        self.events = events
        self.source_name = source_name
        self.priority_label = priority_label
        self.rule_id = rule_id
        self.rule_intent = rule_intent
        self.timestamp_occured_iso8601 = timestamp_occured_iso8601
        self.timestamp_received_iso8601 = timestamp_received_iso8601
        self.rule_attack_tactic = rule_attack_tactic
        self.rule_strategy = rule_strategy
        self.rule_attack_technique = rule_attack_technique
        self.rule_attack_id = rule_attack_id
        self.source_organisation = source_organisation
        self.source_country = source_country
        self.destination_name = destination_name
        self.is_suppressed = is_suppressed

    def to_csv(self):
        return {
            "ID": self.uuid,
            "Priority": self.priority_label,
            "Occurred Time": self.timestamp_occured_iso8601,
            "Received Time": self.timestamp_received_iso8601,
            "Rule Attack ID": self.rule_attack_id,
            "Rule Attack Tactic": (
                " ".join(self.rule_attack_tactic)
                if isinstance(self.rule_attack_tactic, list)
                else self.rule_attack_tactic
            ),
            "Rule Attack Technique": self.rule_attack_technique,
            "Rule ID": self.rule_id,
            "Rule Intent": self.rule_intent,
            "Rule Strategy": self.rule_strategy,
            "Source": self.source_name,
            "Source Organisation": self.source_organisation,
            "Source Country": self.source_country,
            "Destination": self.destination_name,
            "Is Suppressed": self.is_suppressed,
        }


class Event:
    def __init__(
        self,
        raw_data,
        uuid=None,
        event_name=None,
        timestamp_occured_iso8601=None,
        timestamp_received_iso8601=None,
        suppressed=None,
        event_severity=None,
        event_category=None,
        event_subcategory=None,
        access_control_outcome=None,
        destination_name=None,
        destination_port=None,
        source_name=None,
        source_port=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.uuid = uuid
        self.event_name = event_name
        self.timestamp_occured_iso8601 = timestamp_occured_iso8601
        self.timestamp_received_iso8601 = timestamp_received_iso8601
        self.suppressed = suppressed
        self.event_severity = event_severity
        self.event_category = event_category
        self.event_subcategory = event_subcategory
        self.access_control_outcome = access_control_outcome
        self.destination_name = destination_name
        self.destination_port = destination_port
        self.source_name = source_name
        self.source_port = source_port

    def to_csv(self):
        return {
            "ID": self.uuid,
            "Name": self.event_name,
            "Occurred Time": self.timestamp_occured_iso8601,
            "Received Time": self.timestamp_received_iso8601,
            "Suppressed": self.suppressed,
            "Severity": self.event_severity,
            "Category": self.event_category,
            "Subcategory": self.event_subcategory,
            "Access Control Outcome": self.access_control_outcome,
            "Destination": self.destination_name,
            "Destination Port": self.destination_port,
            "Source": self.source_name,
            "Source Port": self.source_port,
        }

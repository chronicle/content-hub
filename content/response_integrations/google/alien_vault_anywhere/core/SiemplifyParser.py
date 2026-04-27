from __future__ import annotations
from .datamodels import AlienVaultAlarmModel, SiemplifyPriorityEnum, Event


class SiemplifyParser:
    def build_siemplify_event_object(self, event):
        """
        Build the event
        :param event: {dict} alienVault event
        :return: {Event}
        """
        return Event(raw_data=event, **event)

    def build_siemplify_alarm_object(self, alarm):
        """
        Build the alarm according to AlienVaultAlarmModel
        :param alarm: {dict} alienVault alarm
        :return: {AlienVaultAlarmModel}
        """
        name = (f'{alarm.get("rule_intent", "")}_{alarm.get("rule_strategy", "")}_'
                f'{alarm.get("rule_method", "")}')

        priority = self.parse_priority(alarm.get("priority", 0))
        uuid = alarm.get("uuid")
        events = alarm.get("events", [])
        timestamp = alarm.get("timestamp_occured", 1)

        try:
            timestamp = int(timestamp)
        except:
            timestamp = 1

        return AlienVaultAlarmModel(
            raw_data=alarm,
            name=name,
            uuid=uuid,
            priority=priority,
            original_priority=alarm.get("priority", 0),
            timestamp=timestamp,
            events=events,
            priority_label=alarm.get("priority_label"),
            timestamp_received=alarm.get("timestamp_received"),
            source_name=alarm.get("source_name"),
            rule_id=alarm.get("rule_id"),
            rule_intent=alarm.get("rule_intent"),
            timestamp_occured_iso8601=alarm.get("timestamp_occured_iso8601"),
            timestamp_received_iso8601=alarm.get("timestamp_received_iso8601"),
            rule_attack_tactic=alarm.get("rule_attack_tactic", []),
            rule_strategy=alarm.get("rule_strategy"),
            rule_attack_technique=alarm.get("rule_attack_technique"),
            rule_attack_id=alarm.get("rule_attack_id"),
            source_organisation=alarm.get("source_organisation"),
            source_country=alarm.get("source_country"),
            destination_name=alarm.get("destination_name"),
            is_suppressed=alarm.get("suppressed"),
        )

    @staticmethod
    def parse_priority(priority):
        """
        Translate AlienVault priorities to Siemplify priorities
        :param priority: {int} The Alienvault priority
        :return: {int} Siemplify priority
        """
        try:
            priority = int(priority)
        except:
            return SiemplifyPriorityEnum.INFO.value

        if priority >= 67 and priority <= 100:
            return SiemplifyPriorityEnum.HIGH.value
        elif priority >= 34 and priority <= 66:
            return SiemplifyPriorityEnum.MEDIUM.value
        elif priority >= 0 and priority <= 33:
            return SiemplifyPriorityEnum.LOW.value

        return SiemplifyPriorityEnum.INFO.value

from __future__ import annotations
from .datamodels import Indicator, Host, Alert, FileAcquisition, GroupAlerts, Ack, Group


class FireEyeHXParser:
    """
    FireEye HX Transformation Layer.
    """

    @staticmethod
    def build_siemplify_indicator_obj(indicator_data):
        return Indicator(raw_data=indicator_data, **indicator_data)

    @staticmethod
    def build_siemplify_host_obj(host_data):
        return Host(raw_data=host_data, **host_data)

    @staticmethod
    def build_siemplify_alert_obj(alert_data):
        return Alert(raw_data=alert_data, **alert_data)

    @staticmethod
    def build_siemplify_file_acquisition_obj(file_acquisition_data):
        return FileAcquisition(raw_data=file_acquisition_data, **file_acquisition_data)

    @staticmethod
    def build_siemplify_group_alert_obj(group_alert_data):
        return GroupAlerts(
            raw_data=group_alert_data,
            id=group_alert_data.get("_id"),
            indicator_display_name=(
                group_alert_data.get("indicator", {}).get("display_name")
                if group_alert_data.get("indicator", {})
                else ""
            ),
            event_at=group_alert_data.get("event_at"),
            matched_at=group_alert_data.get("matched_at"),
            reported_at=group_alert_data.get("reported_at"),
            event_type=group_alert_data.get("event_type"),
            source=group_alert_data.get("source"),
        )

    @staticmethod
    def build_siemplify_ack_obj(ack_data):
        return Ack(
            raw_data=ack_data,
            total=ack_data.get("total"),
            entiries_ids=[ack.get("_id") for ack in ack_data.get("entries", {})],
        )

    @staticmethod
    def build_siemplify_group_obj(group_data):
        return Group(
            raw_data=group_data,
            assessment=group_data.get("assessment"),
            alert_group_id=group_data.get("_id"),
            first_event=group_data.get("first_event_at"),
            last_event=group_data.get("last_event_at"),
            ack=group_data.get("acknowledgement", {}).get("acknowledged"),
            last_event_id=group_data.get("last_alert", {}).get("_id"),
            events_count=group_data.get("stats", {}).get("events"),
            detected_by=group_data.get("grouped_by", {}).get("detected_by"),
        )

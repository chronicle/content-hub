from __future__ import annotations
from .datamodels import *


class FireEyeCMParser:
    def build_alerts_array(self, raw_data):
        alerts_data = raw_data.get("alert", [])
        return [
            self.build_siemplify_alert_obj(alert_data=alert_data)
            for alert_data in alerts_data
        ]

    def build_siemplify_alert_obj(self, alert_data):
        return Alert(
            raw_data=alert_data,
            malwares=alert_data.get("explanation", {})
            .get("malwareDetected", {})
            .get("malware", []),
            cnc_services=alert_data.get("explanation", {})
            .get("cncServices", {})
            .get("cncService", []),
            src=alert_data.get("src", {}),
            url=alert_data.get("alertUrl"),
            action=alert_data.get("action"),
            occurred=alert_data.get("occurred"),
            attack_time=alert_data.get("attackTime"),
            dst=alert_data.get("dst", {}),
            appliance_id=alert_data.get("applianceId"),
            id=alert_data.get("id"),
            name=alert_data.get("name"),
            severity=alert_data.get("severity"),
            uuid=alert_data.get("uuid"),
            ack=alert_data.get("ack"),
            product=alert_data.get("product"),
            vlan=alert_data.get("vlan"),
            malicious=alert_data.get("malicious"),
            sc_version=alert_data.get("scVersion"),
        )

    @staticmethod
    def build_sensor_appliance_obj(raw_sensor):
        return SystemConfiguration.Sensor(
            raw_data=raw_sensor,
            os_details_product=raw_sensor.get("osdetails", [])[0].get("product"),
            **raw_sensor
        )

    @staticmethod
    def build_sys_config_obj(raw_data):
        return SystemConfiguration(
            raw_data=raw_data,
            raw_type=raw_data.get("rawType"),
            sys_type=raw_data.get("type"),
            sensors=[
                FireEyeCMParser.build_sensor_appliance_obj(raw_sensor)
                for raw_sensor in raw_data.get("entity", {}).get("sensors", [])
            ],
        )

    @staticmethod
    def build_ioc_feed_type_obj(feed_type_data):
        return IOCFeed.ContentMeta(
            content_type=feed_type_data.get("contentType"),
            feed_count=feed_type_data.get("feedCount"),
        )

    @staticmethod
    def build_ioc_feed_obj(ioc_data):
        return IOCFeed(
            raw_data=ioc_data,
            feed_name=ioc_data.get("feedName"),
            status=ioc_data.get("status"),
            feed_type=ioc_data.get("feedType"),
            upload_date=ioc_data.get("uploadDate"),
            feed_action=ioc_data.get("feedAction"),
            feed_source=ioc_data.get("feedSource"),
            content_meta_list=[
                FireEyeCMParser.build_ioc_feed_type_obj(feed_type_data)
                for feed_type_data in ioc_data.get("contentMeta", [])
            ],
        )

    @staticmethod
    def build_ioc_feed_obj_list(raw_data, limit=None):
        raw_data = raw_data.get("customFeedInfo", [])
        raw_data = (
            raw_data[:limit] if limit is not None else raw_data
        )  # slice to limit if needed
        return [FireEyeCMParser.build_ioc_feed_obj(ioc_data) for ioc_data in raw_data]

    @staticmethod
    def build_quarantined_email(raw_data):
        return QuarantinedEmail(
            raw_data=raw_data,
            email_uuid=raw_data.get("email_uuid"),
            queue_id=raw_data.get("queue_id"),
            message_id=raw_data.get("message_id"),
            completed_at=raw_data.get("completed_at"),
            sender=raw_data.get("from"),
            subject=raw_data.get("subject"),
            appliance_id=raw_data.get("appliance_id"),
            quarantine_path=raw_data.get("quarantine_path"),
        )

    @staticmethod
    def build_quarantined_email_list(raw_data, limit=None):
        raw_data = (
            raw_data[:limit] if limit is not None else raw_data
        )  # slice to limit if needed
        return [FireEyeCMParser.build_quarantined_email(email) for email in raw_data]

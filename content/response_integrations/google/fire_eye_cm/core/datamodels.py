from __future__ import annotations
import copy
import uuid
from TIPCommon import dict_to_flat

from .FireEyeCMConstants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    FIREEYE_CM_TO_SIEM_SEVERITY,
    IOC_FEED_CONTENT_TYPE_CSV_MAPPING,
)
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Alert:
    def __init__(
        self,
        raw_data,
        malwares=None,
        cnc_services=None,
        src=None,
        url=None,
        action=None,
        occurred=None,
        attack_time=None,
        dst=None,
        appliance_id=None,
        id=None,
        name=None,
        severity=None,
        uuid=None,
        ack=None,
        product=None,
        vlan=None,
        malicious=None,
        sc_version=None,
    ):
        self.raw_data = raw_data
        self.malwares = malwares if malwares else []
        self.cnc_services = cnc_services if cnc_services else []
        self.src = src
        self.url = url
        self.action = action
        self.occurred = occurred
        self.attack_time = attack_time
        self.dst = dst
        self.appliance_id = appliance_id
        self.id = id
        self.name = name
        self.severity = severity
        self.uuid = uuid
        self.ack = ack
        self.product = product
        self.vlan = vlan
        self.malicious = malicious
        self.sc_version = sc_version

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        return FIREEYE_CM_TO_SIEM_SEVERITY.get(self.severity, -1)

    def to_alert_info(self, environment):
        # type: (EnvironmentHandle) -> AlertInfo
        """
        Creates Siemplify Alert Info based on Indicator information
        @param environment: EnvironmentHandle object
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.uuid
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.name
        alert_info.start_time = self.occurred_time_unix
        alert_info.end_time = self.occurred_time_unix
        alert_info.events = (
            [dict_to_flat(event) for event in self.create_events()]
            if self.create_events()
            else [self.to_event()]
        )
        alert_info.environment = environment.get_environment(self.raw_data)

        return alert_info

    def to_event(self):
        return dict_to_flat(self.raw_data)

    def create_events(self):
        events = []

        for malware in self.malwares:
            alert = copy.deepcopy(self.raw_data)
            alert.pop("explanation", None)
            malware["alert"] = alert
            events.append(malware)

        for service in self.cnc_services:
            alert = copy.deepcopy(self.raw_data)
            alert.pop("explanation", None)
            service["alert"] = alert
            events.append(service)

        return events

    @property
    def occurred_time_unix(self):
        return convert_string_to_unix_time(self.occurred)


class SystemConfiguration(BaseModel):
    """
    Configuration Information of FireEye CM
    """

    class Sensor(BaseModel):
        """
        FireEye CM Sensor appliances
        """

        def __init__(
            self,
            raw_data,
            address=None,
            id=None,
            applicanceId=None,
            os_details_product=None,
            sensor_name=None,
            **kwargs,
        ):
            super(SystemConfiguration.Sensor, self).__init__(raw_data)
            self.address = address
            self.id = id
            self.applicanceId = (applicanceId,)
            self.os_details_product = os_details_product
            self.sensor_name = sensor_name

    def __init__(self, raw_data, raw_type=None, sys_type=None, sensors=None):
        super(SystemConfiguration, self).__init__(raw_data)
        self.raw_type = (raw_type,)
        self.sys_type = (sys_type,)
        self.sensors = sensors or []


class QuarantinedEmail(BaseModel):
    """
    Quarantined Email in FireEye CM datamodel
    """

    def __init__(
        self,
        raw_data,
        email_uuid=None,
        queue_id=None,
        message_id=None,
        completed_at=None,
        sender=None,
        subject=None,
        appliance_id=None,
        quarantine_path=None,
    ):
        super(QuarantinedEmail, self).__init__(raw_data)
        self.email_uuid = email_uuid
        self.queue_id = queue_id
        self.message_id = message_id
        self.completed_at = completed_at
        self.sender = sender
        self.subject = subject
        self.appliance_id = appliance_id
        self.quarantine_path = quarantine_path

    def to_csv(self):
        return {
            "Sender": self.sender,
            "Subject": self.subject,
            "Completed At": self.completed_at,
            "Email UUID": self.email_uuid,
            "Message ID": self.message_id,
            "Queue ID": self.queue_id,
        }


class IOCFeed(BaseModel):
    """
    IOC Feed in FireEye CM
    """

    class ContentMeta:
        def __init__(self, content_type=None, feed_count=None):
            self.content_type = content_type
            self.feed_count = feed_count

        def as_csv(self):
            return (
                {
                    f"{IOC_FEED_CONTENT_TYPE_CSV_MAPPING.get(self.content_type, 'UNKNOWN Feed Type')} Count": self.feed_count
                }
                if self.feed_count is not None
                else {}
            )

    def __init__(
        self,
        raw_data,
        feed_name=None,
        status=None,
        feed_type=None,
        upload_date=None,
        feed_action=None,
        feed_source=None,
        content_meta_list=None,
    ):
        super(IOCFeed, self).__init__(raw_data)
        self.feed_name = feed_name
        self.status = status
        self.feed_type = feed_type
        self.upload_date = upload_date
        self.feed_action = feed_action
        self.feed_source = feed_source
        self.content_meta_list = content_meta_list or [IOCFeed.ContentMeta()]

    def as_csv(self):
        csv_table = {
            "Name": self.feed_name,
            "Status": self.status,
            "Type": self.feed_type,
            "Action": self.feed_action,
            "Comment": self.feed_source,
            "Uploaded At": self.upload_date,
        }
        for content_meta in self.content_meta_list:
            csv_table.update(content_meta.as_csv())
        return csv_table

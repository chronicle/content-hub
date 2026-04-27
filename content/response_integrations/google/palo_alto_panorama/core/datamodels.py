from __future__ import annotations
import datetime
import uuid
from dateutil import parser

from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from .PanoramaCommon import convert_server_time_to_datetime

from .PanoramaConstants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    BLACKLIST_FILTER,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    PANORAMA_TO_SIEM_SEVERITY,
    FILE_SUBTYPES,
    URI_SUBTYPE,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class LogEntity(BaseModel):
    def __init__(
        self,
        raw_data,
        log_id,
        seqno,
        receive_time,
        src,
        dst,
        action,
        subtype,
        severity,
        description,
        misc,
        category,
        filedigest,
        filetype,
        matchname,
        repeatcnt,
        device_name,
        tag_name,
        event_id,
        ip,
        user,
        app,
        admin,
        cmd,
        opaque,
        desc,
        time_generated,
        server_time,
    ):
        super(LogEntity, self).__init__(raw_data)
        self.log_id = log_id
        self.seqno = seqno
        self.threat_id = seqno
        self.receive_time = receive_time
        self.src = src
        self.dst = dst
        self.action = action
        self.severity = severity
        self.description = description
        self.misc = misc
        self.subtype = subtype
        self.category = category
        self.filedigest = filedigest
        self.filetype = filetype
        self.matchname = matchname
        self.repeatcnt = repeatcnt
        self.device_name = device_name
        self.tag_name = tag_name
        self.event_id = event_id
        self.ip = ip
        self.user = user
        self.app = app
        self.admin = admin
        self.cmd = cmd
        self.opaque = opaque
        self.desc = desc
        self.time_generated = time_generated
        self.server_time = server_time

    def to_csv(self, log_type):
        data = {}
        if log_type.lower() == "Traffic".lower():
            data = {
                "Receive Time": self.receive_time,
                "Src IP": self.src,
                "Dst IP": self.dst,
                "Action": self.action,
                "Type": self.subtype,
                "Application": self.app,
            }
        elif log_type.lower() == "Threat".lower():
            data = {
                "Receive Time": self.receive_time,
                "Description": self.description,
                "Src IP": self.src,
                "Dst IP": self.dst,
                "Name": self.misc,
                "Type": self.subtype,
                "Severity": self.severity,
            }
        elif log_type.lower() == "URL Filtering".lower():
            data = {
                "Receive Time": self.receive_time,
                "Src IP": self.src,
                "Dst IP": self.dst,
                "URL": self.misc,
                "Category": self.category,
                "Severity": self.severity,
                "Action": self.action,
            }
        elif log_type.lower() == "Wildfire Submissions".lower():
            data = {
                "Receive Time": self.receive_time,
                "Description": self.description,
                "Src IP": self.src,
                "Dst IP": self.dst,
                "Name": self.misc,
                "Type": self.subtype,
                "Severity": self.severity,
                "Action": self.action,
                "Hash": self.filedigest,
                "File Type": self.filetype,
            }
        elif log_type.lower() == "Data Filtering".lower():
            data = {
                "Receive Time": self.receive_time,
                "Description": self.description,
                "Src IP": self.src,
                "Dst IP": self.dst,
                "Name": self.misc,
                "Type": self.subtype,
                "Severity": self.severity,
                "Action": self.action,
            }
        elif log_type.lower() == "HIP Match".lower():
            data = {
                "Receive Time": self.receive_time,
                "IP": self.src,
                "HIP": self.matchname,
                "Repeat Count": self.repeatcnt,
                "Device Name": self.device_name,
            }
        elif log_type.lower() == "IP Tag".lower():
            data = {
                "Receive Time": self.receive_time,
                "IP": self.ip,
                "Tag Name": self.tag_name,
                "Device Name": self.device_name,
                "Event ID": self.event_id,
            }
        elif log_type.lower() == "User ID".lower():
            data = {
                "Receive Time": self.receive_time,
                "IP": self.ip,
                "User": self.user,
                "Device Name": self.device_name,
                "Type": self.subtype,
            }
        elif log_type.lower() == "Tunnel Inspection".lower():
            data = {
                "Receive Time": self.receive_time,
                "Src IP": self.src,
                "Dst IP": self.dst,
                "Application": self.app,
                "Type": self.subtype,
                "Severity": self.severity,
                "Action": self.action,
            }
        elif log_type.lower() == "Configuration".lower():
            data = {
                "Receive Time": self.receive_time,
                "Command": self.cmd,
                "Admin": self.admin,
                "Device Name": self.device_name,
            }
        elif log_type.lower() == "System".lower():
            data = {
                "Receive Time": self.receive_time,
                "Device Name": self.device_name,
                "Type": self.subtype,
                "Severity": self.severity,
                "Description": self.opaque,
            }
        elif log_type.lower() == "Authentication".lower():
            data = {
                "Receive Time": self.receive_time,
                "Device Name": self.device_name,
                "IP": self.ip,
                "User": self.user,
                "Type": self.subtype,
                "Severity": self.severity,
                "Description": self.desc,
            }

        return data

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        return PANORAMA_TO_SIEM_SEVERITY.get(self.severity, -1)

    def to_alert_info(self, environment):
        # type: (EnvironmentHandle) -> AlertInfo
        """
        Creates Siemplify Alert Info based on LogEntity information
        @param environment: EnvironmentHandle object
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.threat_id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.subtype
        alert_info.start_time = convert_datetime_to_unix_time(
            self.naive_time_converted_to_aware
        )
        alert_info.end_time = convert_datetime_to_unix_time(
            self.naive_time_converted_to_aware
        )
        alert_info.events = [self.to_event()]
        alert_info.environment = environment.get_environment(self.raw_data)

        return alert_info

    def to_event(self):
        if self.subtype == URI_SUBTYPE:
            self.raw_data["url"] = self.misc
        elif self.subtype in FILE_SUBTYPES:
            self.raw_data["filename"] = self.misc
        else:
            self.raw_data["url"] = self.misc
            self.raw_data["filename"] = self.misc

        return dict_to_flat(self.raw_data)

    def pass_time_filter(self):
        # type: () -> bool
        """
        Check if now - time_generated is older than acceptable time in minutes
        @return: Is older or not
        """
        return convert_server_time_to_datetime(
            self.server_time
        ) - self.naive_time_converted_to_aware > datetime.timedelta(
            minutes=ACCEPTABLE_TIME_INTERVAL_IN_MINUTES
        )

    def pass_whitelist_or_blacklist_filter(self, rules_list, whitelist_filter_type):
        """
        Determine whether threat pass the whitelist/blacklist filter or not.
        :param rules_list: {list} The rules list provided by user.
        :param whitelist_filter_type: {unicode} whitelist filter type. Possible values are WHITELIST_FILTER, BLACKLIST_FILTER
        :return: {bool} Whether threat pass the whitelist/blacklist filter or not.
        """
        if not rules_list:
            return True

        if whitelist_filter_type == BLACKLIST_FILTER:
            return self.description not in rules_list

        return self.description in rules_list

    @property
    def naive_time_converted_to_aware(self):
        """
        Converts naive time to aware time
        :return: {datetime}
        """
        server_date = convert_server_time_to_datetime(self.server_time)
        parsed_date = parser.parse(self.time_generated)
        return datetime.datetime(
            parsed_date.year,
            parsed_date.month,
            parsed_date.day,
            parsed_date.hour,
            parsed_date.minute,
            parsed_date.second,
            tzinfo=server_date.tzinfo,
        )

from __future__ import annotations
import uuid
import datetime

from TIPCommon import dict_to_flat
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    BLACKLIST_FILTER,
    SYMANTEC_TO_SIEM_PRIORITY,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
)
from soar_sdk.SiemplifyUtils import (
    convert_string_to_unix_time,
    convert_string_to_datetime,
    utc_now,
)
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo


class BaseData:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Comment(BaseData):

    def __init__(self, raw_data, comment=None, time=None, incident_responder_name=None):

        super(Comment, self).__init__(raw_data)
        self.comment = comment
        self.time = time
        self.incident_responder_name = incident_responder_name

    def to_table(self):
        return {
            "Comment": self.comment,
            "Created at": self.time,
            "Source": self.incident_responder_name,
        }


class Incident(BaseData):
    def __init__(
        self,
        raw_data,
        atp_incident_id=None,
        priority_level=None,
        state=None,
        first_event_seen=None,
        last_event_seen=None,
        device_time=None,
        time=None,
        updated=None,
        atp_rule_id=None,
        rule_name=None,
        uuid=None,
        log_name=None,
        recommended_action=None,
        summary=None,
        resolution=None,
        **kwargs
    ):
        super(Incident, self).__init__(raw_data)
        self.atp_incident_id = atp_incident_id
        self.priority_level = priority_level
        self.state = state
        self.first_event_seen = first_event_seen
        self.last_event_seen = last_event_seen
        self.device_time = device_time
        self.time = time
        self.updated = updated
        self.atp_rule_id = atp_rule_id
        self.rule_name = rule_name
        self.uuid = uuid
        self.log_name = log_name
        self.recommended_action = recommended_action
        self.summary = summary
        self.resolution = resolution
        self.events = []

    @property
    def priority(self):
        return SYMANTEC_TO_SIEM_PRIORITY.get(self.priority_level, -1)

    def pass_time_filter(self):
        return utc_now() - convert_string_to_datetime(
            self.device_time
        ) > datetime.timedelta(minutes=ACCEPTABLE_TIME_INTERVAL_IN_MINUTES)

    def to_enrichment_data(self):
        pass

    def to_alert(self, environment):
        alert = AlertInfo()
        alert.ticket_id = self.uuid
        alert.display_id = str(uuid.uuid4())
        alert.name = self.rule_name
        alert.description = self.summary
        alert.device_vendor = DEVICE_VENDOR
        alert.device_product = DEVICE_PRODUCT
        alert.priority = self.priority
        alert.rule_generator = self.atp_rule_id
        alert.start_time = convert_string_to_unix_time(self.first_event_seen)
        alert.end_time = convert_string_to_unix_time(self.last_event_seen)
        alert.events = [dict_to_flat(event) for event in self.events]
        alert.environment = environment.get_environment(self.raw_data)

        return alert

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
            return self.rule_name not in rules_list

        return self.rule_name in rules_list

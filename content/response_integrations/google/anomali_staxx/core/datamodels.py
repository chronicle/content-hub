from __future__ import annotations
import datetime
import uuid
from dateutil import parser

from TIPCommon import dict_to_flat
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from .UtilsManager import get_server_tzoffset

from .AnomaliStaxxConstants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    ANOMALI_STAXX_TO_SIEM_SEVERITY,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Indicator(BaseModel):
    def __init__(
        self,
        raw_data,
        indicator,
        tlp,
        itype,
        severity,
        classification,
        detail,
        confidence,
        actor,
        feed_name,
        source,
        feed_site_netloc,
        campaign,
        type,
        id,
        date_last,
        timezone_offset,
    ):
        super(Indicator, self).__init__(raw_data)
        self.indicator = indicator
        self.tlp = tlp
        self.itype = itype
        self.severity = severity
        self.classification = classification
        self.detail = detail
        self.confidence = confidence
        self.actor = actor
        self.feed_name = feed_name
        self.source = source
        self.feed_site_netloc = feed_site_netloc
        self.campaign = campaign
        self.type = type
        self.id = id
        self.date_last = date_last
        self.custom_name = f"{self.type}:{self.itype}"
        self.timezone_offset = timezone_offset

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        return ANOMALI_STAXX_TO_SIEM_SEVERITY.get(self.severity, -1)

    def to_alert_info(self, environment):
        # type: (EnvironmentHandle) -> AlertInfo
        """
        Creates Siemplify Alert Info based on Indicator information
        @param environment: EnvironmentHandle object
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.custom_name
        alert_info.description = self.feed_name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.itype
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
        self.raw_data[self.type] = self.indicator
        return dict_to_flat(self.raw_data)

    @property
    def naive_time_converted_to_aware(self):
        """
        Converts naive time to aware time
        :return: {datetime}
        """
        parsed_date = parser.parse(self.date_last)
        return datetime.datetime(
            parsed_date.year,
            parsed_date.month,
            parsed_date.day,
            parsed_date.hour,
            parsed_date.minute,
            parsed_date.second,
            tzinfo=get_server_tzoffset(self.timezone_offset),
        )

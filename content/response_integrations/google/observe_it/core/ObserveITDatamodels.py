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
import datetime
import uuid
from soar_sdk.SiemplifyUtils import (
    convert_string_to_unix_time,
    convert_string_to_datetime,
    utc_now,
)
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from .ObserveITConstants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    BLACKLIST_FILTER,
    ACCEPTABLE_TIME_INTERVAL_IN_MINUTES,
    OBSERVE_IT_TO_SIEM_SEVERITY,
)


class BaseData:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Alert(BaseData):
    def __init__(
        self,
        raw_data,
        id=None,
        created_at=None,
        observed_at=None,
        timezone_offset=None,
        session_id=None,
        session_day=None,
        endpoint_id=None,
        user_activity_event_id=None,
        endpoint_name=None,
        domain_name=None,
        login_name=None,
        secondary_domain_name=None,
        secondary_login_name=None,
        remote_host_name=None,
        remote_address=None,
        os=None,
        application_name=None,
        window_title=None,
        process_executable=None,
        command=None,
        command_params=None,
        accessed_url=None,
        accessed_site_name=None,
        severity=None,
        rule_name=None,
        rule_desc=None,
        rule_category_name=None,
        details=None,
        sql_command=None,
        database_name=None,
        sql_user_name=None,
        user_activity_observed_at=None,
        collector_url=None,
        session_url=None,
        event_playback_url=None,
        details_url=None,
        collector_id=None,
        rising_value=None,
        **kwargs
    ):
        super(Alert, self).__init__(raw_data)
        self.id = id
        self.created_at = created_at
        self.observed_at = observed_at
        self.timezone_offset = timezone_offset
        self.session_id = session_id
        self.session_day = session_day
        self.endpoint_id = endpoint_id
        self.user_activity_event_id = user_activity_event_id
        self.endpoint_name = endpoint_name
        self.domain_name = domain_name
        self.login_name = login_name
        self.secondary_domain_name = secondary_domain_name
        self.secondary_login_name = secondary_login_name
        self.remote_host_name = remote_host_name
        self.remote_address = remote_address
        self.os = os
        self.application_name = application_name
        self.window_title = window_title
        self.process_executable = process_executable
        self.command = command
        self.command_params = command_params
        self.accessed_url = accessed_url
        self.accessed_site_name = accessed_site_name
        self.severity = severity
        self.rule_name = rule_name
        self.rule_desc = rule_desc
        self.rule_category_name = rule_category_name
        self.details = details
        self.sql_command = sql_command
        self.database_name = database_name
        self.sql_user_name = sql_user_name
        self.user_activity_observed_at = user_activity_observed_at
        self.collector_url = collector_url
        self.session_url = session_url
        self.event_playback_url = event_playback_url
        self.details_url = details_url
        self.collector_id = collector_id
        self.rising_value = rising_value

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        return OBSERVE_IT_TO_SIEM_SEVERITY.get(self.severity, -1)

    def to_alert_info(self, environment):
        # type: (EnvironmentHandle) -> AlertInfo
        """
        Creates Siemplify Alert Info based on API alert information
        @param environment: EnvironmentHandle object
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.rule_name
        alert_info.description = self.rule_desc
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.rule_category_name
        alert_info.start_time = convert_string_to_unix_time(self.created_at)
        alert_info.end_time = convert_string_to_unix_time(self.created_at)
        alert_info.events = [self.raw_data]
        alert_info.environment = environment.get_environment(self.raw_data)
        alert_info.extensions = {
            "collectorUrl": self.collector_url,
            "sessionUrl": self.session_url,
            "eventPlaybackUrl": self.event_playback_url,
            "detailsUrl": self.details_url,
        }

        return alert_info

    def pass_time_filter(self):
        # type: () -> bool
        """
        Check if now - created_at time is older than acceptable time in minutes
        @return: Is older or not
        """
        return utc_now() - convert_string_to_datetime(
            self.created_at
        ) > datetime.timedelta(minutes=ACCEPTABLE_TIME_INTERVAL_IN_MINUTES)

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

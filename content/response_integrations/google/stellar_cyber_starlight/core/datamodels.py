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
import uuid
from TIPCommon import dict_to_flat
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from .StellarCyberStarlightConstants import DEVICE_VENDOR, DEVICE_PRODUCT, PRE_DISPLAY_ID
from .UtilsManager import find_fallback_value


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Hit(BaseModel):
    def __init__(self, raw_data):
        super(Hit, self).__init__(raw_data)


class ErrorObject(BaseModel):
    def __init__(self, raw_data, message):
        super(ErrorObject, self).__init__(raw_data)
        self.message = message


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        event_category,
        event_name,
        severity,
        timestamp,
        xdr_event_name,
    ):
        super(Alert, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.id = id
        self.event_category = event_category
        self.event_name = event_name
        self.severity = severity
        self.timestamp = timestamp
        self.xdr_event_name = xdr_event_name
        if event_name:
            self.name = (
                f"{event_category.capitalize() if event_category else ''}: {event_name}"
            )
        else:
            self.name = f"{self.raw_data.get('_source', {}) .get('xdr_event', {}) .get('xdr_killchain_stage')}: {self.xdr_event_name}"

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        if self.severity >= 100:
            return 100
        elif self.severity >= 80:
            return 80
        elif self.severity >= 60:
            return 60
        elif self.severity >= 40:
            return 40
        else:
            return -1

    def to_alert_info(
        self,
        environment,
        device_product_field,
        event_class_id,
        product_field_fallback=None,
        event_field_fallback=None,
    ):
        # type: (EnvironmentHandle,str) -> AlertInfo
        """
        Creates Siemplify Alert Info based on Indicator information
        @param environment: EnvironmentHandle object
        @param device_product_field: {str} Field to use for product field
        @param event_class_id: {str} Field to use for event field
        @param product_field_fallback:
            {list} List of fallback fields to use for product field
        @param event_field_fallback:
            {list} List of fallback fields to use for event field
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.id
        alert_info.display_id = PRE_DISPLAY_ID + str(uuid.uuid4())
        alert_info.name = self.name
        if self.event_name:
            alert_info.rule_generator = f"{self.event_category}:{self.event_name}"
        else:
            alert_info.rule_generator = f"{self.raw_data.get('_source', {}) .get('xdr_event', {}) .get('xdr_killchain_stage')}:{self.xdr_event_name}"
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = find_fallback_value(
            source_dicts=[self.flat_raw_data],
            fallbacks_list=[device_product_field] + (product_field_fallback or []),
            default_value=DEVICE_PRODUCT,
        )
        alert_info.priority = self.priority
        alert_info.start_time = self.timestamp
        alert_info.end_time = self.timestamp
        alert_info.events = [self.to_event(event_class_id, event_field_fallback)]
        alert_info.environment = environment.get_environment(self.raw_data)

        return alert_info

    def to_event(self, event_class_id, event_field_fallback=None):
        return {
            "chronicle_event_type": find_fallback_value(
                source_dicts=[self.flat_raw_data],
                fallbacks_list=[event_class_id] + (event_field_fallback or []),
            ),
            **self.flat_raw_data,
        }

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
import copy
import json
from TIPCommon import dict_to_flat, add_prefix_to_dict
from azure_ad_identity_protection.core.constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP, RISK_COLOR_MAP
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.raw_data)

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class User(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        is_deleted,
        is_processing,
        risk_level,
        risk_state,
        risk_detail,
        risk_updated,
        display_name,
        principal_name,
    ):
        super(User, self).__init__(raw_data)
        self.id = id
        self.is_deleted = is_deleted
        self.is_processing = is_processing
        self.risk_level = "No Risk" if risk_level == "none" else risk_level or "No Risk"
        self.risk_state = risk_state
        self.risk_detail = risk_detail
        self.risk_updated = risk_updated
        self.display_name = display_name
        self.principal_name = principal_name

    def to_csv(self):
        table_data = self.to_table()
        table_data["link"] = (
            f"https://portal.azure.com/#blade/Microsoft_AAD_IAM/UserDetailsMenuBlade/Profile/userId/{self.id}"
        )
        return dict_to_flat(table_data)

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_table(self):
        return {
            "is_deleted": self.is_deleted,
            "is_processing": self.is_processing,
            "risk_level": self.risk_level,
            "risk_state": self.risk_state,
            "risk_detail": self.risk_detail,
            "risk_updated": self.risk_updated,
            "display_name": self.display_name,
            "principal_name": self.principal_name,
        }

    def to_insight(self):
        risk_color = RISK_COLOR_MAP.get(self.risk_level.title())
        return (
            f'<table><tbody><tr><td><h2 style="text-align: left;"><strong>Risk Level: <span style="color: '
            f'{risk_color};">{self.risk_level.title()}</span></strong></h2></td><td><h2 style="text-align: '
            f'left;"><strong>&nbsp;State: {self.risk_state}</strong></h2></td></tr></tbody></table><p><strong>'
            f"Display Name: </strong>{self.display_name}<strong><br />Principal Name: </strong>"
            f"{self.principal_name}<strong><br />Risk Detail: </strong>{self.risk_detail}<strong><br />Deleted: "
            f"</strong>{self.is_deleted}<strong><br />Proccessing: </strong>{self.is_processing}<strong><br />"
            f"</strong>&nbsp;</p>"
        )


class RiskDetection(BaseModel):
    def __init__(self, raw_data, id, risk_event_type, risk_level, detected_date_time):
        super(RiskDetection, self).__init__(raw_data)
        self.uuid = str(uuid.uuid4())
        self.id = id
        self.risk_event_type = risk_event_type
        self.risk_level = risk_level
        self.detected_date_time = detected_date_time

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = self.uuid
        alert_info.name = self.risk_event_type
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = self.risk_event_type
        alert_info.end_time = alert_info.start_time = convert_string_to_unix_time(
            self.detected_date_time
        )
        alert_info.events = [self.as_event()]

        return alert_info

    def get_severity(self):
        return SEVERITY_MAP.get(self.risk_level, -1)

    def as_event(self):
        event_data = copy.deepcopy(self.raw_data)
        additional_info = json.loads(event_data.pop("additionalInfo", None))
        for info in additional_info:
            event_data[info.get("Key", "")] = info.get("Value", "")
        return dict_to_flat(event_data)

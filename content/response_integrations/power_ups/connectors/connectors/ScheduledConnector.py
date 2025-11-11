# Copyright 2025 Google LLC
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

import json
import uuid

from soar_sdk import SiemplifyUtils
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import output_handler

VENDOR = "Siemplify"


@output_handler
def generate_alert(product_name, alert_name, alert_type, alert_fields):
    alert_id = str(uuid.uuid4())
    case_info = CaseInfo()
    case_info.events = []
    case_info.source_grouping_identifier = alert_id
    case_info.ticket_id = alert_id
    case_info.display_id = alert_id

    if alert_type:
        case_info.rule_generator = alert_type
    else:
        case_info.rule_generator = "Scheduled Alert"

    print(alert_name)
    if alert_name:
        case_info.name = alert_name
    else:
        case_info.name = "Scheduled Alert - " + alert_id

    case_info.device_product = product_name
    print("product_name - " + product_name)
    for alert_field in alert_fields:
        case_info.extensions[alert_field.strip()] = alert_fields[alert_field]

    case_info.priority = (
        60  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    )
    case_info.start_time = SiemplifyUtils.unix_now()  # Times should be saved in UnixTime. You may use SiemplifyUtils DateTime conversions
    case_info.end_time = SiemplifyUtils.unix_now()

    case_info.device_vendor = VENDOR

    event = generate_event(case_info)
    case_info.events.append(event)

    return case_info


def generate_event(case_info):
    event = {}

    event["StartTime"] = SiemplifyUtils.unix_now()
    event["EndTime"] = SiemplifyUtils.unix_now()
    event["name"] = case_info.name
    event["event_type"] = case_info.rule_generator
    event["device_product"] = case_info.device_product

    return event


@output_handler
def main():
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper

    product_name = siemplify.extract_connector_param("Product name")
    alert_name = siemplify.extract_connector_param("Alert name")
    alert_type = siemplify.extract_connector_param("Alert type")
    alert_fields_str = siemplify.parameters["Alert fields"]

    alert_fields = json.loads(alert_fields_str)

    output_variables = {}
    log_items = []
    cases = []

    alert_obj = generate_alert(product_name, alert_name, alert_type, alert_fields)
    cases.append(alert_obj)
    print(json.dumps(cases[0].__dict__))
    siemplify.return_package(cases, output_variables, log_items)


if __name__ == "__main__":
    main()

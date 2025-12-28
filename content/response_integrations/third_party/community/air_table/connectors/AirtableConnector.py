from __future__ import annotations

import uuid

from airtable import Airtable
from soar_sdk import SiemplifyUtils
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import output_handler

VENDOR = "AirTable"
PRODUCT = "AirTable"


@output_handler
def generate_alert_from_record(record, alert_type, alert_name_field, alert_name_prefix):
    case_info = CaseInfo()
    case_info.events = []
    case_info.source_grouping_identifier = str(uuid.uuid4())
    case_info.ticket_id = str(uuid.uuid4())
    case_info.device_product = PRODUCT
    case_info.device_vendor = VENDOR
    for field in record["fields"]:
        if field == "Type":
            case_info.extensions["Record_Type"] = record["fields"][field]
        else:
            case_info.extensions[field.replace(" ", "_")] = record["fields"][field]
    if alert_name_field:
        case_info.name = record["fields"][alert_name_field]
        if alert_name_prefix:
            case_info.name = alert_name_prefix + case_info.name
    else:
        case_info.name = "AT Record " + str(uuid.uuid4())
    case_info.rule_generator = alert_type
    case_info.priority = (
        60  # Informative = -1,Low = 40,Medium = 60,High = 80,Critical = 100.
    )
    case_info.start_time = SiemplifyUtils.unix_now()  # Times should be saved in UnixTime. You may use SiemplifyUtils DateTime conversions
    case_info.end_time = SiemplifyUtils.unix_now()
    # case_info.device_vendor = VENDOR
    event = generate_event(case_info)
    case_info.events.append(event)
    return case_info


def generate_event(case_info):
    event = {}
    for keyName in case_info.extensions.keys():
        event[keyName] = case_info.extensions[keyName]
    event["StartTime"] = SiemplifyUtils.unix_now()
    event["EndTime"] = SiemplifyUtils.unix_now()
    event["name"] = case_info.name
    event["event_type"] = case_info.rule_generator
    event["device_product"] = PRODUCT
    return event


@output_handler
def main():
    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    env_list = []
    api_key = siemplify.extract_connector_param("Api key")
    base_id = siemplify.extract_connector_param("Base id")
    table_name = siemplify.extract_connector_param("Table name")
    field_name = siemplify.extract_connector_param("Field name", default_value=None)
    field_value = siemplify.extract_connector_param("Field value", default_value=None)
    max_records_str = str(siemplify.extract_connector_param("Max records"))
    alert_name_field = siemplify.extract_connector_param(
        "Alert name field",
        default_value=None,
    )
    alert_name_prefix = siemplify.extract_connector_param(
        "Alert name prefix",
        default_value=None,
    )
    alert_type = siemplify.extract_connector_param("Alert type", default_value=None)
    max_records = 5
    try:
        max_records = int(max_records_str)
    except ValueError:
        print(max_records_str + " is not an int!")
    airtable = Airtable(base_id, table_name, api_key)
    records = []
    if field_name:
        fields = field_value.split(",")
        for field in fields:
            query_results = airtable.search(
                field_name,
                field.strip(),
                maxRecords=max_records,
            )
            records = records + query_results
    else:
        records = airtable.get_all(maxRecords=max_records)
    output_variables = {}
    log_items = []
    cases = []
    for record in records:
        case_from_record = generate_alert_from_record(
            record,
            alert_type,
            alert_name_field,
            alert_name_prefix,
        )
        cases.append(case_from_record)
    siemplify.return_package(cases, output_variables, log_items)


if __name__ == "__main__":
    main()

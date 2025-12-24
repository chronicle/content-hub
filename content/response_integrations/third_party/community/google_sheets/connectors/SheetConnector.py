from __future__ import annotations

import sys
import uuid

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.google_sheets import GoogleSheetFactory

CONNECTOR_NAME = "Google Sheet Connector"
PROPERTY_KEY = "credentials"


@output_handler
def main(is_test_run):
    alerts = []  # The main output of each connector run

    siemplify = SiemplifyConnectorExecution()  # Siemplify main SDK wrapper
    siemplify.script_name = CONNECTOR_NAME

    credentials_json = siemplify.extract_connector_param(
        param_name="Credentials Json",
        is_mandatory=True,
    )
    sheet_id = siemplify.extract_connector_param(
        param_name="Sheet Id",
        is_mandatory=True,
    )
    worksheet_name = siemplify.extract_connector_param(param_name="Worksheet Name")
    filter_alert_column_index = siemplify.extract_connector_param(
        param_name="Filter Alert Column Index",
    )
    filter_alert_column_value = siemplify.extract_connector_param(
        param_name="Filter Alert Column Value",
    )
    product = siemplify.extract_connector_param(param_name="Product")
    alert_name_column_index = siemplify.extract_connector_param(
        param_name="Alert Name Column Index",
        is_mandatory=True,
    )
    alert_name_column_index_int = int(alert_name_column_index)

    sheet = GoogleSheetFactory(credentials_json).create_spreadsheet(sheet_id)

    if worksheet_name:
        worksheet = sheet.worksheet(worksheet_name)
    else:
        worksheet = sheet.sheet1

    headers = worksheet.row_values(1)

    all_rows_values = worksheet.get_all_values()

    for row in all_rows_values[1:]:
        if len(row) > 2:
            if filter_alert_column_index and filter_alert_column_value:
                filter_alert_column_index_int = int(filter_alert_column_index)
                if (
                    row[filter_alert_column_index_int].lower()
                    != filter_alert_column_value.lower()
                ):
                    continue

            alert_info = AlertInfo()

            alert_id = str(uuid.uuid4())
            alert_info.display_id = alert_id
            alert_info.ticket_id = alert_id
            alert_info.name = product

            if alert_name_column_index_int != -1:
                alert_info.name = "<" + row[alert_name_column_index_int] + ">"
            else:
                alert_info.name = product
            alert_info.rule_generator = product
            alert_info.start_time = unix_now()
            alert_info.end_time = unix_now()
            alert_info.priority = 60
            alert_info.device_vendor = CONNECTOR_NAME
            alert_info.device_product = product
            alert_info.environment = (
                siemplify.context.connector_info.environment
            )  # This field, gets the Environment of the specific connector execution.
            print(alert_info.name)

            event = {}

            index = 0
            event["StartTime"] = unix_now()
            event["EndTime"] = unix_now()
            event["name"] = product
            event["device_product"] = product

            for cell in row:
                event[headers[index]] = cell
                index = index + 1
            alert_info.events.append(event)
            alerts.append(alert_info)

    print(f"{len(alerts)} alert was successfully generated.")
    siemplify.return_package(alerts)


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)

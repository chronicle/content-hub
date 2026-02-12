from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.NSMManager import NsmManager

# Consts
ACTION_SCRIPT_NAME = "NSM Get Alert Details"
NSM_PROVIDER = "McAfeeNSM"
TABLE_NAME = "Alert Details: {0}"


@output_handler
def main():
    # Define variables.
    result_value = ""

    # Configuration.
    siemplify = SiemplifyAction()
    # Script Name.
    siemplify.script_name = ACTION_SCRIPT_NAME
    conf = siemplify.get_configuration(NSM_PROVIDER)
    nsm_manager = NsmManager(
        conf["API Root"],
        conf["Username"],
        conf["Password"],
        conf["Domain ID"],
        conf["Siemplify Policy Name"],
        conf["Sensors Names List Comma Separated"],
    )

    # Parameters.
    alert_id = siemplify.parameters.get("Alert ID")
    sensor_name = siemplify.parameters.get("Sensor Name")

    alert_data = nsm_manager.get_alert_info_by_id(alert_id, sensor_name)

    if alert_data:
        result_value = json.dumps(alert_data)
        siemplify.result.add_json(TABLE_NAME.format(alert_id), result_value)

    if result_value:
        output_message = f'Found alert info data for alert with ID - "{alert_id}"'
    else:
        output_message = f'Not found alert info data for alert with ID - "{alert_id}"'

    siemplify.result.add_result_json(alert_data)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

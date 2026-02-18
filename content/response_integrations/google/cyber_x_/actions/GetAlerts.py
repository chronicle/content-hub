from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat, construct_csv
from ..core.CyberXManager import CyberXManager
import json

ACTION_NAME = "CyberX_Get Alerts"
PROVIDER = "CyberX"
TABLE_TITLE = "Result ALerts"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    config = siemplify.get_configuration(PROVIDER)
    api_root = config["API Root"]
    access_token = config["Access Token"]
    verify_ssl = config.get("Verify SSL", "false").lower() == "true"

    cyberx_manager = CyberXManager(
        api_root=api_root, access_token=access_token, verify_ssl=verify_ssl
    )

    alerts = cyberx_manager.get_alerts()

    if alerts:
        siemplify.result.add_data_table(TABLE_TITLE, construct_csv(list(map(dict_to_flat, alerts))))
        output_message = f"{len(alerts)} alerts were found."
    else:
        output_message = "No alerts were found."

    siemplify.end(output_message, json.dumps(alerts))


if __name__ == "__main__":
    main()

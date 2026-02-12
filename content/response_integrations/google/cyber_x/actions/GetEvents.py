from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, dict_to_flat, output_handler

from ..core.CyberXManager import CyberXManager

ACTION_NAME = "CyberX_Get Events"
PROVIDER = "CyberX"
TABLE_TITLE = "Result Events"


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

    events = cyberx_manager.get_events() or []

    if events:
        siemplify.result.add_data_table(TABLE_TITLE, construct_csv(list(map(dict_to_flat, events))))
        output_message = f"{len(events)} events were found."
    else:
        output_message = "No events were found."

    siemplify.end(output_message, json.dumps(events))


if __name__ == "__main__":
    main()

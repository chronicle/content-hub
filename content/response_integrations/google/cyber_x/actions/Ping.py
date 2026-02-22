from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CyberXManager import CyberXManager

ACTION_NAME = "CyberX_Ping"
PROVIDER = "CyberX"


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

    cyberx_manager.get_all_devices()

    siemplify.end("Connection established.", True)


if __name__ == "__main__":
    main()

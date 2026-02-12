from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.JuniperVSRXManager import JuniperVSRXManager

PROVIDER_NAME = "JuniperVSRX"
ACTION_NAME = "JuniperVSRX Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    config = siemplify.get_configuration(PROVIDER_NAME)
    address = config["Address"]
    port = config["Port"]
    username = config["Username"]
    password = config["Password"]

    juniper_manager = JuniperVSRXManager(address, port, username, password)
    result_value = False

    if juniper_manager.ping():
        output_message = "Connection Established."
        result_value = True
    else:
        output_message = "Connection Failed."

    juniper_manager.close_session()

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

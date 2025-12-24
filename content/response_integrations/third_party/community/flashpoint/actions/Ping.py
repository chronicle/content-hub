from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.FlashpointManager import FlashpointManager

IDENTIFIER = "Flash Point"


@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")

    # Creating an instance of FlashPoint object
    flashpoint_manager = FlashpointManager(api_key)

    # Calling the function test_connectivity() from the FlashpointManager
    response = flashpoint_manager.test_connectivity()

    if response:
        return_value = True
        output_message = "Connected successfully"

    else:
        return_value = False
        output_message = "The Connection failed"

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()

from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AsanaManager import AsanaManager

IDENTIFIER = "Asana"


@output_handler
def main():
    siemplify = SiemplifyAction()

    personal_access_token = siemplify.extract_configuration_param(IDENTIFIER, "Token")
    base_url = siemplify.extract_configuration_param(IDENTIFIER, "Base URL")

    # Creating an instance of AsanaManager object
    asana_manager = AsanaManager(personal_access_token, base_url)

    # Calling the function test_connectivity() from the AsanaManager
    response = asana_manager.test_connectivity()

    if response:
        return_value = True
        output_message = "Connected successfully"

    else:
        return_value = False
        output_message = "The Connection failed"

    # Test connectivity
    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()

from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DataDogManager import DataDogManager

IDENTIFIER = "DataDog"


@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")
    app_key = siemplify.extract_configuration_param(IDENTIFIER, "APP Key")

    datadog_manager = DataDogManager(api_key, app_key)

    connection_response = datadog_manager.test_connectivity()

    if connection_response.get("valid") == True:
        return_value = True
        output_message = "Connected successfully"

    else:
        return_value = False
        output_message = "The Connection failed"

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()

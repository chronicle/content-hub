from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.DoppelManager import DoppelManager

# Example Constants
INTEGRATION_NAME = "DoppelVision"
SCRIPT_NAME = "Ping"


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    # Initialize Integration Configuration
    api_key = siemplify.extract_configuration_param(
        provider_name="DoppelVision",
        param_name="API_Key",
    )
    user_api_key = siemplify.extract_configuration_param(
        provider_name="DoppelVision",
        param_name="User_API_Key",
    )
    org_code = siemplify.extract_configuration_param(
        provider_name="DoppelVision",
        param_name="Organization_Code",
    )

    # Debugging: Log the retrieved API key
    siemplify.LOGGER.info(f"Extracted API Key: {api_key}")

    if not api_key:
        siemplify.end("API key is missing or could not be retrieved.", "false")
        return

    # Create an instance of the DoppelManager
    doppel_manager = DoppelManager(
        api_key=api_key,
        user_api_key=user_api_key,
        org_code=org_code
    )

    # Perform Ping
    try:
        if doppel_manager.connection_test():
            siemplify.end("Connection successful", "true")
        else:
            siemplify.end("Connection failed. Invalid API Key or endpoint.", "false")
    except Exception as e:
        siemplify.end(f"An error occurred during Ping: {e!s}", "false")


if __name__ == "__main__":
    main()

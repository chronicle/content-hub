from __future__ import annotations

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION = "Azure DevOps"


@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    personal_access_token = siemplify.extract_configuration_param(
        INTEGRATION,
        "Personal Access Token",
    )
    organization = siemplify.extract_configuration_param(INTEGRATION, "Organization")
    base_url = siemplify.extract_configuration_param(INTEGRATION, "Base URL")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        credentials = BasicAuthentication("", personal_access_token)
        connection = Connection(
            base_url=f"{base_url}/{organization}",
            creds=credentials,
        )
        core_client = connection.clients.get_core_client()

        # Get the first page of projects
        core_client.get_projects()

    except Exception as e:
        result_value = False
        output_message = f"The Connection failed: {e}"
        status = EXECUTION_STATE_COMPLETED
    else:
        result_value = True
        output_message = "Connected successfully"
        siemplify.LOGGER.info("Connected successfully")
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(
        f"\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

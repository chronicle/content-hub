from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import ACCOUNT_USAGE_SCRIPT_NAME, INTEGRATION_NAME
from ..core.TeamCymruScoutException import TeamCymruScoutException
from ..core.utils import (
    create_api_usage_table,
    get_integration_params,
    render_data_table,
)


@output_handler
def main():
    """Account Usage action is used to fetch the account usage details from Team Cymru Scout."""
    siemplify = SiemplifyAction()

    auth_type, api_key, username, password, verify_ssl = get_integration_params(
        siemplify,
    )

    try:
        api_manager = ApiManager(
            auth_type,
            api_key,
            username,
            password,
            siemplify.LOGGER,
            verify_ssl,
        )

        is_success, response = api_manager.api_usage()

        if is_success is False:
            raise TeamCymruScoutException(response)

        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully fetched the Account Usage details for {INTEGRATION_NAME} API"
        )

        siemplify.result.add_result_json(response)

        account_usage = create_api_usage_table(response)
        render_data_table(siemplify, "Account Usage", account_usage)

    except Exception as e:
        is_success = False
        response = str(e)

        siemplify.LOGGER.error(
            f"Error occurred while performing action: {ACCOUNT_USAGE_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(response)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the {INTEGRATION_NAME} server! Error: {response}"
        )

    result_value = is_success

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

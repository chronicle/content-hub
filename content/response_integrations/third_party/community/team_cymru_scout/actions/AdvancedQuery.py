from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ApiManager import ApiManager
from ..core.constants import ERRORS, INTEGRATION_NAME, SCOUT_SEARCH_SCRIPT_NAME
from ..core.ScoutSearch import ScoutSearch
from ..core.TeamCymruScoutException import TeamCymruScoutException
from ..core.utils import (
    create_api_usage_table,
    get_integration_params,
    render_data_table,
)


@output_handler
def main():
    """Advanced Query action fetches the summary information available for the given query following the Scout query language."""
    siemplify = SiemplifyAction()

    auth_type, api_key, username, password, verify_ssl = get_integration_params(
        siemplify,
    )

    try:
        scout_search = ScoutSearch(siemplify)

        if scout_search.error:
            raise TeamCymruScoutException(scout_search.error)

        api_manager = ApiManager(
            auth_type,
            api_key,
            username,
            password,
            siemplify.LOGGER,
            verify_ssl,
        )
        is_success, response = scout_search.scout_search(api_manager)

        if is_success is False:
            raise TeamCymruScoutException(response)

        status = EXECUTION_STATE_COMPLETED
        output_message = f"Successfully searched the Query: '{scout_search.query}' from {INTEGRATION_NAME}."
        siemplify.result.add_result_json(response)

        if not response.get("ips", []):
            siemplify.LOGGER.warning(ERRORS["VALIDATIONS"]["NO_IPS_RESPONSE"])
            output_message += "\n" + ERRORS["VALIDATIONS"]["NO_IPS_RESPONSE"]
        else:
            scout_search.generate_tables()

        account_usage = create_api_usage_table(response.get("usage", {}))
        render_data_table(siemplify, "Account Usage", account_usage)

    except Exception as e:
        is_success = False
        response = str(e)
        siemplify.LOGGER.error(
            f"General error performing action {SCOUT_SEARCH_SCRIPT_NAME}.",
        )
        siemplify.LOGGER.exception(response)

        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to fetch data for the given query!\nError: {response}"

    result_value = is_success

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

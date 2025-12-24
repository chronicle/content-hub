from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.FlashpointManager import FlashpointManager

IDENTIFIER = "Flash Point"
SCRIPT_NAME = "Flashpoint - Custom Query"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")

    results_limit = siemplify.extract_action_param("Limit")
    start_date = siemplify.extract_action_param("Start Date")
    end_date = siemplify.extract_action_param("End Date")
    search_tags = siemplify.extract_action_param("Search Tags")
    query = siemplify.extract_action_param("Query")
    sort_timestamp = siemplify.extract_action_param("Sort By Time")
    attributes_types = siemplify.extract_action_param("Entity Types")
    basetypes_path = siemplify.extract_action_param("Indicator Type")

    # Creating an instance of FlashPoint object
    flashpoint_manager = FlashpointManager(api_key)

    try:
        # Sending the query by the function indicators_custom_query().
        query_results = flashpoint_manager.indicators_custom_query(
            results_limit,
            start_date,
            end_date,
            search_tags,
            query,
            sort_timestamp,
            attributes_types,
            basetypes_path,
        )
        if query_results:
            return_value = True
            output_message = "The query results were fetched successfully"
            siemplify.result.add_result_json(query_results)
        else:
            return_value = False
            output_message = "The Entities were not found in Flashpoint"

    except Exception as e:
        output_message = "Error fetching results from Flashpoint"
        siemplify.LOGGER.error(
            f"Error fetching results from the Flashpoint, Error: {e}.",
        )
        siemplify.LOGGER.exception(e)

    siemplify.end(output_message, return_value)


if __name__ == "__main__":
    main()

from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.FlashpointManager import FlashpointManager

ADDRESS = EntityTypes.ADDRESS
SCRIPT_NAME = "Flashpoint - Run Query"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    conf = siemplify.get_configuration("Flashpoint")
    api_key = conf["API Key"]

    query_content = siemplify.extract_action_param("Query")
    result_count_limit = siemplify.extract_action_param("Results count limit")
    date_range = siemplify.extract_action_param("Date Range")
    sort_by = siemplify.extract_action_param("Sort By")
    tags = siemplify.extract_action_param("Tags")

    flashpoint_manager = FlashpointManager(api_key)

    query_response = flashpoint_manager.run_custom_query(
        query_content,
        result_count_limit,
        date_range,
        sort_by,
        tags,
    )

    result_value = True
    output_message = "The query was sent successfully"

    # add json
    siemplify.result.add_result_json(query_response)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DataDogManager import DataDogManager

IDENTIFIER = "DataDog"


@output_handler
def main():
    siemplify = SiemplifyAction()
    result_value = False
    output_message = ""

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")
    app_key = siemplify.extract_configuration_param(IDENTIFIER, "APP Key")

    query_to_search = siemplify.extract_action_param("Query")
    start_time = siemplify.extract_action_param("Start Time")
    end_time = siemplify.extract_action_param("End Time")

    datadog_manager = DataDogManager(api_key, app_key)

    snapshot_graph = datadog_manager.get_graph_snapshot(
        query_to_search,
        start_time,
        end_time,
    )

    if bool(snapshot_graph) == True:
        siemplify.LOGGER.info(
            f"The graph snapshot of the query {query_to_search} was fetched successfully",
        )
        result_value = True
        output_message = f"The graph snapshot of the query {query_to_search} was fetched successfully"

    else:
        siemplify.LOGGER.info(
            f"The graph snapshot of the query {query_to_search} wasn't fetched.",
        )
        output_message = (
            f"The graph snapshot of the query {query_to_search} wasn't fetched."
        )

    # Adding the snapshot URL link
    title = "The graph snapshot URL"
    link = snapshot_graph.get("snapshot_url")
    siemplify.result.add_link(title, link)

    siemplify.result.add_result_json(snapshot_graph)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

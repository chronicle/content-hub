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

    metrics_timeseries_points = datadog_manager.get_timeseries_point_metrics(
        query_to_search,
        start_time,
        end_time,
    )
    if (
        metrics_timeseries_points.get("status") == "ok"
        and len(metrics_timeseries_points.get("series")) > 0
    ):
        siemplify.LOGGER.info(
            f"The timeseries points of the query {query_to_search} were found successfully",
        )
        result_value = True
        output_message = f"The timeseries points of the query {query_to_search} were found successfully"

    else:
        siemplify.LOGGER.info(
            f"The metric for the query {query_to_search} wasn't found.",
        )
        output_message = f"The metrics for the query '{query_to_search}' wasn't found."

    siemplify.result.add_result_json(metrics_timeseries_points)

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

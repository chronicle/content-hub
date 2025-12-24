from __future__ import annotations

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DataDogManager import DataDogManager

IDENTIFIER = "DataDog"


@output_handler
def main():
    siemplify = SiemplifyAction()
    result_value = False
    output_message = ""
    json_result = {}
    raw_metric_values = []
    sum_of_metric_values = 0
    average_of_metric_values = 0
    min_of_metric_values = None
    max_of_metric_values = None

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")
    app_key = siemplify.extract_configuration_param(IDENTIFIER, "APP Key")

    series = siemplify.extract_action_param("Series")
    series = json.loads(series)

    datadog_manager = DataDogManager(api_key, app_key)
    print(series)
    if series.get("pointlist") is not None:
        siemplify.LOGGER.info("The series parameter is valid.")
        # Analyzing the metric timeseries points
        timeseries_points = series.get("pointlist")
        start_time = series.get("start")
        end_time = series.get("end")

        try:
            for value in timeseries_points:
                raw_metric_values.append(value[1])

            siemplify.LOGGER.info(f"The raw metric values are: {raw_metric_values}")

            # Calculating the sum of all the raw_metric_values
            sum_of_metric_values = sum(raw_metric_values)
            siemplify.LOGGER.info(
                f"The sum of the metric timeseries points between {start_time} to {end_time} is {sum_of_metric_values}",
            )

            # Calculating the average of all the raw_metric_values
            average_of_metric_values = sum(raw_metric_values) / len(raw_metric_values)
            siemplify.LOGGER.info(
                f"The average of the metric timeseries points between {start_time} to {end_time} is {average_of_metric_values}",
            )

            # Calculating the minimum of all the raw_metric_values
            min_of_metric_values = min(raw_metric_values)
            siemplify.LOGGER.info(
                f"The minimum value of the metric values between {start_time} to {end_time} is {min_of_metric_values}",
            )

            # Calculating the maximum of all raw_metric_values
            max_of_metric_values = max(raw_metric_values)
            siemplify.LOGGER.info(
                f"The maximum value of the metric values between {start_time} to {end_time} is {max_of_metric_values}",
            )

            json_result["unit"] = series.get("unit")[0].get("family")
            json_result["aggregation_by"] = series.get("aggr")
            json_result["start_time"] = start_time
            json_result["end_time"] = end_time
            json_result["full_timeseries_points_list"] = timeseries_points
            json_result["sum_of_the_metric_values"] = sum_of_metric_values
            json_result["average_of_the_metric_values"] = average_of_metric_values
            json_result["min_of_the_metric_values"] = min_of_metric_values
            json_result["max_of_the_metric_values"] = max_of_metric_values
            json_result["expression"] = series.get("expression")

        except Exception as e:
            siemplify.LOGGER.error(
                f"Error occured when analyzing the timeseries points of the series {series}.\nError: {e}",
            )

    else:
        siemplify.LOGGER.error(
            "The series parameter is not valid, please check your query again.",
        )

    siemplify.result.add_result_json(json_result)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

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

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")
    app_key = siemplify.extract_configuration_param(IDENTIFIER, "APP Key")

    sources = siemplify.extract_action_param("Sources")
    start_time = siemplify.extract_action_param("Start Time")
    end_time = siemplify.extract_action_param("End Time")
    tags = siemplify.extract_action_param("Tags")
    priority = siemplify.extract_action_param("Priority")
    unaggregated = siemplify.extract_action_param("Unaggregated", input_type=bool)

    datadog_manager = DataDogManager(api_key, app_key)

    events = datadog_manager.get_datadog_events(
        start_time,
        end_time,
        sources,
        tags,
        priority,
        unaggregated,
    )
    print(json.dumps(events))
    if len(events) > 0:
        siemplify.LOGGER.info(
            f"The events from the source {sources} were fetched successfully.",
        )
        result_value = True
        output_message = (
            f"The events from the source {sources} were fetched successfully."
        )

    else:
        siemplify.LOGGER.info(f"The events from the source {sources} weren't fetched.")
        output_message = f"The events from the source {sources} weren't fetched."

    siemplify.result.add_result_json(events)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

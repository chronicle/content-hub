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

    event_id = siemplify.extract_action_param("Event ID")

    datadog_manager = DataDogManager(api_key, app_key)

    event_details = datadog_manager.get_event_details(event_id)

    if event_details:
        siemplify.LOGGER.info(
            f"The event details of {event_id} were fetched successfully.",
        )
        result_value = True
        output_message = f"The event details of {event_id} were fetched successfully."

    else:
        siemplify.LOGGER.info(f"The event details of {event_id} were not fetched.")
        output_message = f"The event details of {event_id} were not fetched."

    siemplify.result.add_result_json(event_details)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

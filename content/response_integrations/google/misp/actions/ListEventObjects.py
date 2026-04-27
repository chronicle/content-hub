from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_EVENT_OBJECTS_SCRIPT_NAME,
    EVENT_OBJECT_TABLE_NAME,
)
from ..core.utils import string_to_multi_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_EVENT_OBJECTS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    api_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )

    event_ids = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Event ID", print_value=True, is_mandatory=True
        )
    )

    limit = extract_action_param(
        siemplify, param_name="Max Objects to Return", print_value=True, input_type=int
    )
    limit = limit if limit and limit > 0 else None

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    json_result = []
    misp_events = []
    found_events_ids = []
    not_found_events_ids = []

    try:
        misp_manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)
        fetched_events = 0
        for event_id in event_ids:
            try:
                events_to_add = limit - fetched_events if limit else None
                if fetched_events == limit:
                    break

                events = misp_manager.get_event_objects(event_id, events_to_add)
                fetched_events += len(events)

                if not events:
                    not_found_events_ids.append(event_id)
                    continue

                misp_events.append((event_id, events))

            except Exception as e:
                siemplify.LOGGER.error(f"An error occurred on event {event_id}")
                siemplify.LOGGER.exception(e)
                not_found_events_ids.append(event_id)

        for event_id, events in misp_events:
            json_result.extend(events)
            found_events_ids.append(event_id)
            siemplify.result.add_data_table(
                EVENT_OBJECT_TABLE_NAME.format(event_id),
                construct_csv([event.to_csv() for event in events]),
            )

        if json_result:
            siemplify.result.add_result_json(
                [found_event.to_object_json() for found_event in json_result]
            )

        if found_events_ids:
            output_message += f'Successfully listed objects for the following events: {", ".join(found_events_ids)}\n'

        if not_found_events_ids:
            output_message += f'Action wasn’t able to find objects for the following events: {", ".join(not_found_events_ids)}\n'

        if not found_events_ids:
            output_message = "No objects were found for the provided events."

    except Exception as e:
        output_message = (
            f'Error executing action "{LIST_EVENT_OBJECTS_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

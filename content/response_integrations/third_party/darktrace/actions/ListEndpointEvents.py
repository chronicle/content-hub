from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    DEVICE_KEYS,
    EVENT_TYPES,
    EVENT_TYPES_NAMES,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    LIST_ENDPOINT_EVENTS_SCRIPT_NAME,
    PARAMETERS_DEFAULT_DELIMITER,
)
from ..core.DarktraceExceptions import (
    IncompleteInformationException,
    InvalidTimeException,
    NegativeValueException,
)
from ..core.DarktraceManager import DarktraceManager
from ..core.UtilsManager import get_timestamps

# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()
SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.MACADDRESS,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ENDPOINT_EVENTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=True,
    )
    api_private_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Private Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    event_type_string = extract_action_param(
        siemplify, param_name="Event Type", is_mandatory=True, print_value=True
    )
    timeframe = extract_action_param(
        siemplify, param_name="Time Frame", is_mandatory=True, print_value=True
    )
    start_time_string = extract_action_param(siemplify, param_name="Start Time", print_value=True)
    end_time_string = extract_action_param(siemplify, param_name="End Time", print_value=True)
    limit = extract_action_param(
        siemplify, param_name="Max Events To Return", input_type=int, print_value=True
    )

    event_types = (
        [
            event_type.strip()
            for event_type in event_type_string.split(PARAMETERS_DEFAULT_DELIMITER)
            if event_type.strip()
        ]
        if event_type_string
        else []
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        if [event_type for event_type in event_types if event_type not in EVENT_TYPES]:
            raise IncompleteInformationException

        if limit < 0:
            raise NegativeValueException

        start_time, end_time = get_timestamps(timeframe, start_time_string, end_time_string)

        manager = DarktraceManager(
            api_root=api_root,
            api_token=api_token,
            api_private_token=api_private_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        manager.test_connectivity()

        if limit:
            for entity in suitable_entities:
                siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")

                try:
                    if entity.entity_type == EntityTypes.ADDRESS:
                        device = manager.get_devices(DEVICE_KEYS.get("ip"), entity.identifier)
                    elif entity.entity_type == EntityTypes.HOSTNAME:
                        device = manager.search_devices_by_hostname(entity.identifier)
                    else:
                        device = manager.get_devices(DEVICE_KEYS.get("mac"), entity.identifier)

                    if device and device.did:
                        entity_events = {}

                        for event_type in event_types:
                            events = manager.get_events_for_endpoint(
                                device.did, event_type, start_time, end_time, limit
                            )

                            if events:
                                entity_events[event_type] = events

                        if entity_events:
                            successful_entities.append(entity)
                            json_results[entity.identifier] = {
                                event_type: [event.to_json() for event in events]
                                for event_type, events in entity_events.items()
                            }

                            for event_type, events in entity_events.items():
                                siemplify.result.add_data_table(
                                    title=f"{entity.identifier}: {EVENT_TYPES_NAMES[event_type]}",
                                    data_table=construct_csv([
                                        event.to_table(EVENT_TYPES_NAMES[event_type])
                                        for event in events
                                    ]),
                                )

                        else:
                            failed_entities.append(entity)
                    else:
                        failed_entities.append(entity)

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed processing entities: {entity.identifier}: Error is: {e}"
                    )
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        if successful_entities:
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
            output_message += (
                "Successfully returned events related to the following endpoints from {}: \n{}"
            ).format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if failed_entities:
            output_message += (
                "\nAction wasn't able to find any events related to the following "
                "endpoints from {}: \n{}"
            ).format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result = False
            output_message = "No events were found for the provided endpoints."

    except NegativeValueException:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_ENDPOINT_EVENTS_SCRIPT_NAME}". Reason: '
            f'"Max Events To Return" should be a positive number.'
        )
    except InvalidTimeException:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_ENDPOINT_EVENTS_SCRIPT_NAME}". Reason: "Start Time" '
            f'should be provided, when "Custom" is selected in "Time Frame" parameter.'
        )
    except IncompleteInformationException:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_ENDPOINT_EVENTS_SCRIPT_NAME}". Reason: Invalid values '
            f'was provided in the parameter "Event Type". '
            f"Possible values: {PARAMETERS_DEFAULT_DELIMITER.join(EVENT_TYPES)}."
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_ENDPOINT_EVENTS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{LIST_ENDPOINT_EVENTS_SCRIPT_NAME}." Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

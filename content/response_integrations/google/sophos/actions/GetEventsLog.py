from __future__ import annotations
import datetime
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    dict_to_flat,
    utc_now,
    construct_csv,
    convert_dict_to_json_result_dict,
    convert_datetime_to_unix_time,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.SophosManager import SophosManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import GET_EVENTS_LOG_SCRIPT_NAME, INTEGRATION_NAME
from ..core.utils import get_entity_original_identifier, validated_limit

SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_EVENTS_LOG_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siem_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="SIEM API Root",
        input_type=str,
    )

    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Key", input_type=str
    )

    base64_payload = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Base 64 Auth Payload",
        input_type=str,
    )

    time_delta = extract_action_param(
        siemplify,
        param_name="Timeframe",
        is_mandatory=True,
        default_value=12,
        input_type=int,
    )
    limit = extract_action_param(
        siemplify, param_name="Max Events To Return", default_value=50, input_type=int
    )

    if time_delta > 24:
        time_delta = 24
    start_time = utc_now() - datetime.timedelta(hours=time_delta)
    start_time = int(convert_datetime_to_unix_time(start_time) / 1000)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        validated_limit(limit)
        manager = SophosManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siem_api_root=siem_api_root,
            api_key=api_key,
            api_token=base64_payload,
            test_connectivity=False,
        )
        status = EXECUTION_STATE_COMPLETED
        successful_entities, failed_entities, no_events_entities, json_result = (
            [],
            [],
            [],
            {},
        )
        result_value = True
        output_message = ""
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITIES
        ]

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            entity_type = entity.entity_type
            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                endpoint = manager.find_entities(
                    entity_identifier=entity_identifier, entity_type=entity_type
                )

                if not endpoint:
                    siemplify.LOGGER.info(
                        f"Endpoint was not found for entity {entity_identifier}. "
                        "Skipping."
                    )
                    failed_entities.append(entity_identifier)
                    continue

                # Get endpoint's events
                events = manager.get_events_by_endpoint(
                    endpoint_id=endpoint.scan_id, since=start_time, limit=limit
                )

                if not events:
                    no_events_entities.append(entity_identifier)
                    siemplify.LOGGER.info(
                        f"No events were found for entity {entity_identifier}"
                    )
                    continue

                flat_events = []
                json_result[entity_identifier] = {
                    "events": [event.to_json() for event in events]
                }
                for event in events:
                    flat_events.append(dict_to_flat(event.to_csv()))

                csv_output = construct_csv(flat_events)
                siemplify.result.add_entity_table(entity_identifier, csv_output)

                successful_entities.append(entity_identifier)
                siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)
        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

        if failed_entities:
            output_message += (
                "\nThe following entities were not found in {}:"
                "\n   {}\n".format(INTEGRATION_NAME, ", ".join(failed_entities))
            )
        if no_events_entities:
            output_message += (
                "\nNo events were found for the following endpoints in {}:"
                "\n   {}\n".format(INTEGRATION_NAME, ", ".join(no_events_entities))
            )
        if successful_entities:
            output_message += (
                "Successfully retrieved events related to the following endpoints in {}:"
                "\n   {}\n".format(INTEGRATION_NAME, ", ".join(successful_entities))
            )
        elif failed_entities and not no_events_entities:
            output_message = (
                f"None of the provided entities were found in {INTEGRATION_NAME}."
            )
            result_value = False
        elif not failed_entities and no_events_entities:
            output_message = (
                "No events were found for the provided endpoints in "
                f"{INTEGRATION_NAME}."
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error occurred while running action {GET_EVENTS_LOG_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f"Error executing action {GET_EVENTS_LOG_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

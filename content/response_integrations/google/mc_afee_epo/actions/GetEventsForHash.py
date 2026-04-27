from __future__ import annotations
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    GET_EVENTS_FOR_HASH_SCRIPT_NAME,
    EVENTS_FOR_HASH_INSIGHT_NAME,
    TIME_FRAME_MAPPING,
    TimeFrameEnum,
)
from ..core.exceptions import McAfeeInvalidParamException
from ..core.utils import get_entity_original_identifier, string_to_multi_value, get_time_frame

SUPPORTED_ENTITY_TYPES = [EntityTypes.FILEHASH]
FIELDS_TO_RETURN_SEPARATOR = ","
EVENTS_DEFAULT_LIMIT = 50


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_EVENTS_FOR_HASH_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ServerAddress",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    group_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="GroupName"
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    fetch_from_epe = extract_action_param(
        siemplify,
        param_name="Fetch Events From EPExtendedEvent Table",
        default_value=False,
        input_type=bool,
    )
    mark_as_suspicious = extract_action_param(
        siemplify, param_name="Mark As Suspicious", input_type=bool, default_value=True
    )
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", input_type=bool, default_value=False
    )
    fields_to_return = string_to_multi_value(
        string_value=extract_action_param(siemplify, param_name="Fields To Return")
    )

    sort_field = extract_action_param(siemplify, param_name="Sort Field")
    sort_order = extract_action_param(siemplify, param_name="Sort Order")

    events_limit = extract_action_param(
        siemplify,
        param_name="Max Events To Return",
        input_type=int,
        default_value=EVENTS_DEFAULT_LIMIT,
    )
    events_limit = events_limit and max(0, events_limit) or EVENTS_DEFAULT_LIMIT

    time_frame = extract_action_param(siemplify, param_name="Time Frame")
    start_time = extract_action_param(siemplify, param_name="Start Time")
    end_time = extract_action_param(siemplify, param_name="End Time")
    is_custom_time_range = time_frame == TimeFrameEnum.CUSTOM.value

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    success_entities, failed_entities, entities_to_update, json_result, csv_result = (
        set(),
        set(),
        [],
        {},
        {},
    )

    try:
        if is_custom_time_range:
            if not start_time:
                raise McAfeeInvalidParamException(
                    '"Start Time" should be provided, when "Custom" is selected in "Time Frame" parameter.'
                )

            start_time, end_time = get_time_frame(
                start_time=start_time, end_time=end_time
            )
            siemplify.LOGGER.info(
                f"The time range to fetch from is: ({start_time} - {end_time})"
            )
        elif time_frame:
            unix_now_time = unix_now()
            # start time an end_time in milliseconds
            start_time, end_time = (
                unix_now_time - TIME_FRAME_MAPPING[time_frame],
                unix_now_time,
            )
            siemplify.LOGGER.info(
                f"The time range to fetch from is: ({start_time} - {end_time})"
            )
        else:
            start_time = end_time = None

        manager = McafeeEpoManager(
            api_root=api_root,
            username=username,
            password=password,
            group_name=group_name,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        suitable_entities = {
            get_entity_original_identifier(entity): entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        }

        entity_identifiers = set(suitable_entities.keys())

        if entity_identifiers:
            request_time_range = (
                (start_time, end_time) if start_time and end_time else None
            )

            vse_events = manager.get_events_by_hash_with_vse_query(
                md5_hashes=entity_identifiers,
                sort_field=sort_field,
                sort_order=sort_order,
                time_range=request_time_range,
                limit=events_limit,
            )
            epe_events = (
                manager.get_events_by_hash_with_epe_query(
                    md5_hashes=entity_identifiers,
                    sort_field=sort_field,
                    sort_order=sort_order,
                    time_range=request_time_range,
                    limit=events_limit,
                )
                if fetch_from_epe
                else []
            )

            for event in vse_events + epe_events:
                entity = suitable_entities.get(event.md5_hash)

                if not entity:
                    continue

                event.visible_json_fields = fields_to_return

                if create_insight:
                    siemplify.add_entity_insight(entity, EVENTS_FOR_HASH_INSIGHT_NAME)

                if mark_as_suspicious:
                    entity.is_suspicious = True
                    entities_to_update.append(entity)

                if not json_result.get(event.md5_hash):
                    json_result[event.md5_hash], csv_result[event.md5_hash] = [], []

                json_result[event.md5_hash].append(event.to_json())
                csv_result[event.md5_hash].append(event.to_csv())
                success_entities.add(event.md5_hash)

            for entity_identifier, event_csv in csv_result.items():
                siemplify.result.add_entity_table(
                    entity_identifier, construct_csv(event_csv)
                )

            failed_entities = entity_identifiers - success_entities

        if entities_to_update:
            siemplify.update_entities(entities_to_update)

        if success_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )
            output_message = (
                "Successfully returned available events for the following hashes in "
                f'{PRODUCT_NAME}: {", ".join(success_entities)}\n'
            )
            if failed_entities:
                output_message += (
                    "Action wasn't able to find events for the following hashes in "
                    f'{PRODUCT_NAME}: {", ".join(failed_entities)}\n'
                )
        else:
            result_value = False
            output_message = (
                f"No events were found for the provided endpoints in {PRODUCT_NAME}."
            )

    except Exception as e:
        output_message = (
            f"Error executing action '{GET_EVENTS_FOR_HASH_SCRIPT_NAME}'. Reason: {e}"
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

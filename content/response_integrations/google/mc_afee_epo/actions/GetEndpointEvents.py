from __future__ import annotations
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    GET_ENDPOINT_EVENTS_SCRIPT_NAME,
    SortOrderEnum,
    TIME_FRAME_MAPPING,
    TimeFrameEnum,
    ENDPOINT_EVENTS_ENTITY_TABLE_NAME,
)
from ..core.exceptions import McAfeeInvalidParamException
from ..core.utils import (
    string_to_multi_value,
    dotted_field_to_underscored,
    get_time_frame,
    get_entity_original_identifier,
    get_entity_type,
    get_existing_list,
    underscored_field_to_dotted,
)

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.MACADDRESS,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ENDPOINT_EVENTS_SCRIPT_NAME
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

    fields_to_return = string_to_multi_value(
        string_value=extract_action_param(siemplify, param_name="Fields To Return")
    )

    # ordering params
    sort_field = underscored_field_to_dotted(
        extract_action_param(siemplify, param_name="Sort Field")
    )
    sort_order = extract_action_param(
        siemplify, param_name="Sort Order", default_value=SortOrderEnum.ASC.value
    )

    events_limit = extract_action_param(
        siemplify, param_name="Max Events To Return", input_type=int, default_value=50
    )

    # time params
    time_frame = extract_action_param(siemplify, param_name="Time Frame")
    start_time = extract_action_param(siemplify, param_name="Start Time")
    end_time = extract_action_param(siemplify, param_name="End Time")
    is_custom_time_range = time_frame == TimeFrameEnum.CUSTOM.value

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    success_entities, failed_entities, entities_to_update, json_result = [], [], [], {}

    try:
        if is_custom_time_range:
            if not start_time:
                raise McAfeeInvalidParamException(
                    '"Start Time" should be provided, when "Custom" is selected in "Time Frame" parameter.'
                )

            start_time, end_time = get_time_frame(
                start_time=start_time, end_time=end_time, validate=False
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
            logger=siemplify.LOGGER,
        )

        suitable_entities = {
            get_entity_original_identifier(entity): entity
            for entity in siemplify.target_entities
            if get_entity_type(entity.entity_type) in SUPPORTED_ENTITY_TYPES
        }

        entity_type_with_key_mapping = {
            EntityTypes.ADDRESS: "ip_addresses",
            EntityTypes.HOSTNAME: "hostnames",
            EntityTypes.MACADDRESS: "mac_addresses",
        }

        endpoints_with_types = {
            get_entity_type(key): [] for key in entity_type_with_key_mapping.values()
        }

        for entity_identifier, entity in suitable_entities.items():
            get_existing_list(
                endpoints_with_types,
                entity_type_with_key_mapping[get_entity_type(entity.entity_type)],
            ).append(entity_identifier)

        execute_entity_params = {
            "table_name": "EPOEvents",
            "sort_field": sort_field,
            "sort_order": sort_order,
            "time_range": (start_time, end_time) if start_time and end_time else None,
            "limit": events_limit,
            "fields_to_return": [
                underscored_field_to_dotted(field) for field in fields_to_return
            ],
        }

        for entity_type, entities in endpoints_with_types.items():
            for entity_identifier in entities:
                request_params = execute_entity_params.copy()
                request_params[entity_type] = entity_identifier
                events = manager.get_endpoint_events(**request_params)

                if not events:
                    failed_entities.append(entity_identifier)
                    continue

                csv_result, json_result[entity_identifier] = [], []

                for event in events:
                    event.visible_json_fields = [
                        dotted_field_to_underscored(field) for field in fields_to_return
                    ]
                    csv_result.append(event.to_csv())
                    json_result[entity_identifier].extend([event.to_json()])

                siemplify.result.add_entity_table(
                    ENDPOINT_EVENTS_ENTITY_TABLE_NAME.format(entity_identifier),
                    construct_csv(csv_result),
                )

                success_entities.append(entity_identifier)

        if success_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )
            output_message = (
                "Successfully returned available events for the following endpoints in "
                f'{PRODUCT_NAME}: {", ".join(map(str, success_entities))}\n'
            )
            if failed_entities:
                output_message += (
                    "Action wasn't able to find events for the following endpoints in "
                    f'{PRODUCT_NAME}: {", ".join(map(str, failed_entities))}\n'
                )
        else:
            result_value = False
            output_message = (
                f"No events were found for the provided endpoints in {PRODUCT_NAME}."
            )
    except Exception as e:
        output_message = (
            f"Error executing action '{GET_ENDPOINT_EVENTS_SCRIPT_NAME}'. Reason: {e}"
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

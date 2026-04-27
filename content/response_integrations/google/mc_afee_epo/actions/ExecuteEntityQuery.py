from __future__ import annotations
from enum import Enum

from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    EXECUTE_ENTITY_QUERY_SCRIPT_NAME,
    TIME_FRAME_MAPPING,
    TimeFrameEnum,
    CROSS_ENTITY_OPERATOR_MAPPING,
    QueryOperatorEnum,
    QUERY_RESULTS_TABLE_NAME,
)
from ..core.exceptions import McAfeeInvalidParamException, McAfeeEpoMissingEntityException
from ..core.utils import (
    get_entity_original_identifier,
    string_to_multi_value,
    get_time_frame,
    get_existing_list,
    get_valid_emails,
    underscored_field_to_dotted,
)


class EventKeyByEntityTypeEnum(Enum):
    IP = "ip_address"
    HOST = "host_name"
    URL = "url"
    HASH = "hash"
    USER = "user"
    EMAIL = "email"


SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.USER,
    EntityTypes.FILEHASH,
    EntityTypes.URL,
]


ENTITY_DATA_LEY_WITH_TYPE_MAPPING = {
    EntityTypes.ADDRESS: EventKeyByEntityTypeEnum.IP.value,
    EntityTypes.HOSTNAME: EventKeyByEntityTypeEnum.HOST.value,
    EntityTypes.USER: EventKeyByEntityTypeEnum.USER.value,
    EntityTypes.FILEHASH: EventKeyByEntityTypeEnum.HASH.value,
    EntityTypes.URL: EventKeyByEntityTypeEnum.URL.value,
}

EVENTS_DEFAULT_LIMIT = 50


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_ENTITY_QUERY_SCRIPT_NAME
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
    table_name = extract_action_param(
        siemplify, param_name="Table Name", is_mandatory=True
    )

    results_limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        default_value=EVENTS_DEFAULT_LIMIT,
    )
    results_limit = results_limit and max(0, results_limit) or EVENTS_DEFAULT_LIMIT

    fields_to_return = string_to_multi_value(
        string_value=extract_action_param(siemplify, param_name="Fields To Return")
    )

    # ordering params
    sort_field = underscored_field_to_dotted(
        extract_action_param(siemplify, param_name="Sort Field")
    )
    sort_order = extract_action_param(siemplify, param_name="Sort Order")

    # time params
    time_frame = extract_action_param(siemplify, param_name="Time Frame")
    is_custom_time_range = time_frame == TimeFrameEnum.CUSTOM.value
    start_time = extract_action_param(siemplify, param_name="Start Time")
    end_time = extract_action_param(siemplify, param_name="End Time")

    # entity params
    ip_entity_key = underscored_field_to_dotted(
        extract_action_param(siemplify, param_name="IP Entity Key")
    )
    hostname_entity_key = underscored_field_to_dotted(
        extract_action_param(siemplify, param_name="Hostname Entity Key")
    )
    file_hash_entity_key = underscored_field_to_dotted(
        extract_action_param(siemplify, param_name="File Hash Entity Key")
    )
    user_entity_key = underscored_field_to_dotted(
        extract_action_param(siemplify, param_name="User Entity Key")
    )
    url_entity_key = underscored_field_to_dotted(
        extract_action_param(siemplify, param_name="URL Entity Key")
    )
    email_address_entity_key = underscored_field_to_dotted(
        extract_action_param(siemplify, param_name="Email Address Entity Key")
    )

    stop_if_not_enough_entities = extract_action_param(
        siemplify,
        param_name="Stop If Not Enough Entities",
        input_type=bool,
        is_mandatory=True,
        default_value=False,
    )
    cross_entity_operator = extract_action_param(
        siemplify,
        param_name="Cross Entity Operator",
        is_mandatory=True,
        default_value=QueryOperatorEnum.OR.name,
    )
    cross_entity_operator = CROSS_ENTITY_OPERATOR_MAPPING[cross_entity_operator]

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = f"No results were found for the provided query in {PRODUCT_NAME}."
    json_result, csv_result = [], []

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
            logger=siemplify.LOGGER,
        )
        suitable_entities = {
            get_entity_original_identifier(entity): entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        }

        entities_with_types = {field.value: [] for field in EventKeyByEntityTypeEnum}

        for entity_identifier, entity in suitable_entities.items():
            get_existing_list(
                entities_with_types,
                ENTITY_DATA_LEY_WITH_TYPE_MAPPING[entity.entity_type],
            ).append(entity_identifier)

        get_existing_list(
            entities_with_types, EventKeyByEntityTypeEnum.EMAIL.value
        ).extend(
            get_valid_emails(entities_with_types[EventKeyByEntityTypeEnum.USER.value])
        )

        entities_with_types[EventKeyByEntityTypeEnum.USER.value] = list(
            set(entities_with_types[EventKeyByEntityTypeEnum.USER.value]).difference(
                set(entities_with_types[EventKeyByEntityTypeEnum.EMAIL.value])
            )
        )

        if stop_if_not_enough_entities:
            event_prop_by_type = {
                EventKeyByEntityTypeEnum.IP.value: ip_entity_key,
                EventKeyByEntityTypeEnum.HOST.value: hostname_entity_key,
                EventKeyByEntityTypeEnum.HASH.value: file_hash_entity_key,
                EventKeyByEntityTypeEnum.USER.value: user_entity_key,
                EventKeyByEntityTypeEnum.URL.value: url_entity_key,
                EventKeyByEntityTypeEnum.EMAIL.value: email_address_entity_key,
            }

            for prop_type, prop_key in event_prop_by_type.items():
                if prop_key and not entities_with_types[prop_type]:
                    raise McAfeeEpoMissingEntityException(
                        "Action wasn't able to build the query, because not enough entity types were supplied for the "
                        'specified "..Entity Keys". Please disable "Stop If Not Enough Entities" parameter or provide '
                        'at least one entity for each specified "..Entity Key".'
                    )

        execute_entity_params = {
            "table_name": table_name,
            "sort_field": sort_field,
            "sort_order": sort_order,
            "cross_entity_operator": cross_entity_operator,
            "ip_entity_key": ip_entity_key,
            "hostname_entity_key": hostname_entity_key,
            "file_hash_entity_key": file_hash_entity_key,
            "user_entity_key": user_entity_key,
            "url_entity_key": url_entity_key,
            "email_address_entity_key": email_address_entity_key,
            "ip_addresses": entities_with_types[EventKeyByEntityTypeEnum.IP.value],
            "hostnames": entities_with_types[EventKeyByEntityTypeEnum.HOST.value],
            "users": entities_with_types[EventKeyByEntityTypeEnum.USER.value],
            "emails": entities_with_types[EventKeyByEntityTypeEnum.EMAIL.value],
            "hashes": entities_with_types[EventKeyByEntityTypeEnum.HASH.value],
            "urls": entities_with_types[EventKeyByEntityTypeEnum.URL.value],
            "time_range": (start_time, end_time) if start_time and end_time else None,
            "limit": results_limit,
            "fields_to_return": [field.replace("_", ".") for field in fields_to_return],
        }

        entity_results = manager.execute_entity_query(**execute_entity_params)

        for event in entity_results:
            json_result.append(event.to_json())
            csv_result.append(event.to_csv())

        if json_result:
            output_message = f"Successfully returned results for the provided query in {PRODUCT_NAME}\n"
            siemplify.result.add_result_json(json_result)
            siemplify.result.add_data_table(
                QUERY_RESULTS_TABLE_NAME, construct_csv(csv_result)
            )
    except McAfeeEpoMissingEntityException as e:
        result_value = False
        output_message = str(e)
    except Exception as e:
        output_message = (
            f"Error executing action '{EXECUTE_ENTITY_QUERY_SCRIPT_NAME}'. Reason: {e}"
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

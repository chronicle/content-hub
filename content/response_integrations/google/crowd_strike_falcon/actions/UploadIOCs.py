# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator

from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    INTEGRATION_NAME,
    UPLOAD_IOCS_SCRIPT_NAME,
    PRODUCT_NAME,
    TYPES_IOC_MAPPER,
    SUPPORTED_HASH_TYPES,
    IOC_PLATFORM_VALUES,
    ACTION_TYPE_DETECT,
    ACTION_TYPE_BLOCK,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.utils import (
    calculate_date,
    get_hash_type,
    get_domain_from_entity,
    get_entity_original_identifier,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)


DEFAULT_SOURCE = "Siemplify"
IOC_TYPE_DEFAULT_VALUES = string_to_multi_value("ipv4,ipv6,md5,sha256,domain")


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPLOAD_IOCS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API Secret"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )
    customer_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True,
    )

    platform = extract_action_param(
        siemplify, param_name="Platform", is_mandatory=True, print_value=True
    )
    severity = extract_action_param(
        siemplify, param_name="Severity", is_mandatory=True, print_value=True
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)
    host_group_name = extract_action_param(
        siemplify, param_name="Host Group Name", is_mandatory=False, print_value=True
    )
    action = extract_action_param(
        siemplify,
        param_name="Action",
        default_value=ACTION_TYPE_DETECT,
        is_mandatory=False,
        print_value=True,
    )
    expiration_days = extract_action_param(
        siemplify,
        param_name="Days To Expire",
        print_value=True,
    )

    platforms = convert_comma_separated_to_list(platform)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    successful_entities, failed_entities = [], []

    try:
        if not all(platform in IOC_PLATFORM_VALUES for platform in platforms):
            raise Exception(
                f'Invalid value provided for the parameter "Platform". Possible values: '
                f"{convert_list_to_comma_string(IOC_PLATFORM_VALUES)}."
            )

        validator: ParameterValidator = ParameterValidator(siemplify)
        if expiration_days is not None:
            expiration_days: int | None = validator.validate_positive(
                param_name="Days To Expire",
                value=expiration_days,
            )
        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in TYPES_IOC_MAPPER.keys()
        ]
        if host_group_name:
            host_group = manager.get_host_group_by_name(host_group_name)
            if not host_group:
                raise Exception(
                    "Invalid host group name provided. Please check the spelling."
                )
            host_group_ids = [host_group.id]
        else:
            host_group_ids = []

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)

            entity_type = TYPES_IOC_MAPPER[entity.entity_type]
            ioc_value = (
                entity_identifier
                if entity.entity_type != EntityTypes.URL
                else get_domain_from_entity(entity_identifier)
            )

            try:
                ioc_type = (
                    entity_type
                    if entity_type
                    else get_entity_hash_type(entity_identifier)
                )
                if action == ACTION_TYPE_BLOCK and ioc_type not in SUPPORTED_HASH_TYPES:
                    siemplify.LOGGER.info(
                        f"Action {ACTION_TYPE_BLOCK} applicable only to IOC's of "
                        f"MD5/SHA256 Hash types. Action {ACTION_TYPE_DETECT} will "
                        f"be applied to entity:{entity_identifier}"
                    )
                    correct_action = ACTION_TYPE_DETECT
                else:
                    correct_action = action
            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.exception(e)
                siemplify.LOGGER.error(
                    f"Invalid hash type. Skip on entity: {entity_identifier}."
                )
                continue

            try:
                if not ioc_type or not ioc_value:
                    raise

                manager.upload_ioc(
                    ioc_type=ioc_type,
                    ioc_value=ioc_value,
                    platforms=platforms,
                    severity=severity,
                    host_group_ids=host_group_ids,
                    action=correct_action,
                    comment=comment,
                    expiration_date=(
                        calculate_date(days=expiration_days)
                        if expiration_days
                        else None
                    ),
                )
                successful_entities.append(entity_identifier)
            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_identifier}. {e}."
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = (
                f"Successfully added the following custom IOCs in {PRODUCT_NAME}: "
                f"{', '.join(successful_entities)}\n"
            )
            if failed_entities:
                output_message += (
                    f"Action wasn't able to add the following custom IOCs in {PRODUCT_NAME}: "
                    f"{', '.join(failed_entities)}\n"
                )
        else:
            output_message = f"None of the custom IOCs were added in {PRODUCT_NAME}.\n"
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action '{UPLOAD_IOCS_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def get_entity_hash_type(entity_identifier):
    hash_type = get_hash_type(entity_identifier)
    if hash_type not in SUPPORTED_HASH_TYPES:
        raise

    return hash_type


if __name__ == "__main__":
    main()

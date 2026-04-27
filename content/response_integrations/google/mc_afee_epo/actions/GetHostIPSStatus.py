from __future__ import annotations
from ..core.McAfeeCommon import McAfeeCommon
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    construct_csv,
)
from TIPCommon import extract_configuration_param
from ..core.constants import (
    GET_HOSTS_IPS_STATUS_SCRIPT_NAME,
    INTEGRATION_NAME,
    HOST_IPS_STATUS_TABLE_NAME,
    PRODUCT_NAME,
)
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
JSON_RESULT_STATUS_KEY = "IPS_status"
CSV_RESULT_STATUS_KEY = "Host IPS Status"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_HOSTS_IPS_STATUS_SCRIPT_NAME
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

    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, systems_data, csv_result, json_result = (
        [],
        [],
        [],
        [],
        {},
    )
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = McafeeEpoManager(
            api_root=api_root,
            username=username,
            password=password,
            group_name=group_name,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        if manager.group and suitable_entities:
            systems_data = manager.get_systems(manager.group.group_id)

        for entity in suitable_entities:
            identifier = get_entity_original_identifier(entity)
            siemplify.LOGGER.info(f"Started processing entity: {identifier}")

            try:
                if manager.group:
                    McAfeeCommon.filter_systems_by_entity(systems_data, entity)

                hip_property = manager.get_host_ips_status(identifier)
                if hip_property:
                    json_result[identifier] = hip_property.to_json(
                        status_key=JSON_RESULT_STATUS_KEY
                    )
                    csv_result.append(
                        hip_property.to_csv(
                            entity_identifier=identifier,
                            status_key=CSV_RESULT_STATUS_KEY,
                        )
                    )
                    successful_entities.append(identifier)
            except Exception as err:
                failed_entities.append(identifier)
                siemplify.LOGGER.error(f"Failed processing entity {identifier}")
                siemplify.LOGGER.exception(err)

            siemplify.LOGGER.info(f"Finished processing entity {identifier}")

        if successful_entities:
            output_message += (
                "Successfully retrieved IPS information from the following endpoints in "
                f"{PRODUCT_NAME}: {', '.join(successful_entities)} \n"
            )
            siemplify.result.add_data_table(
                HOST_IPS_STATUS_TABLE_NAME, construct_csv(csv_result)
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

            if failed_entities:
                output_message += (
                    "Action wasn't able to retrieve IPS information from the following endpoints "
                    f"in {PRODUCT_NAME}: {', '.join(failed_entities)}"
                )
        else:
            output_message = (
                "No information about IPS was found on the provided endpoints."
            )
            result_value = False

    except Exception as err:
        result_value = False
        output_message = (
            f"Error executing action {GET_HOSTS_IPS_STATUS_SCRIPT_NAME}. Reason: {err}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

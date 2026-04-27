from __future__ import annotations
from ..core.McAfeeCommon import McAfeeCommon
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, PRODUCT_NAME, RUN_FULL_SCAN_SCRIPT_NAME
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = RUN_FULL_SCAN_SCRIPT_NAME
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

    task_name = extract_action_param(
        siemplify, param_name="Task Name", print_value=False, is_mandatory=True
    )

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    success_entities, failed_entities, systems_data, json_result = [], [], [], {}

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

        client_task = manager.get_task_by_name_or_raise(task_name=task_name)

        if suitable_entities:
            systems_data = manager.get_systems_by_self_group()

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity}")
            entity_original_identifier = get_entity_original_identifier(entity)
            try:
                manager.get_system_info_or_raise(entity_original_identifier)

                full_scan_task_status = (
                    manager.run_full_scan_by_system_id(
                        client_task=client_task,
                        system_id=McAfeeCommon.filter_systems_by_entity(
                            systems_data, entity
                        ).parent_id,
                    )
                    if group_name
                    else manager.run_full_scan_by_system_name(
                        client_task, system_name=entity_original_identifier
                    )
                )

                if full_scan_task_status.is_success:
                    json_result[entity_original_identifier] = (
                        full_scan_task_status.to_json()
                    )
                    success_entities.append(entity_original_identifier)
                else:
                    failed_entities.append(entity_original_identifier)

            except Exception as e:
                failed_entities.append(entity_original_identifier)
                siemplify.LOGGER.error(
                    f"Failed to run scan for entity {entity_original_identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(
                f"Finished processing entity {entity_original_identifier}"
            )

        if success_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )
            output_message = (
                f'Successfully run full scan based on the task "{task_name}" on the following endpoints'
                f" in {PRODUCT_NAME}: {', '.join(success_entities)}\n"
            )
            if failed_entities:
                output_message += (
                    f'Action wasn\'t able to run full scan based on the task "{task_name}" on the '
                    f"following endpoints in {PRODUCT_NAME}: {', '.join(failed_entities)}"
                )
        else:
            output_message = "Full scan wasn't executed on the provided endpoints."
            result_value = False
    except Exception as e:
        output_message = (
            f"Error executing action '{RUN_FULL_SCAN_SCRIPT_NAME}'. Reason: {e}"
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

from __future__ import annotations
from ..core.McAfeeCommon import McAfeeCommon
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, UPDATE_MCAFEE_AGENT_SCRIPT_NAME, PRODUCT_NAME
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_MCAFEE_AGENT_SCRIPT_NAME
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
        siemplify, param_name="Task Name", is_mandatory=True
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_entities, failed_entities, system_data, json_result = [], [], [], {}
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

        task = manager.get_task_by_name_or_raise(task_name=task_name)

        if suitable_entities:
            system_data = manager.get_systems_by_self_group()

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
            try:
                if manager.group:
                    McAfeeCommon.filter_systems_by_entity(system_data, entity)

                agent_status = manager.update_mcafee_agent(
                    entity=entity_identifier, task=task
                )
                json_result[entity_identifier] = agent_status.to_json()
                successful_entities.append(entity_identifier)
            except Exception as err:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(f"Failed processing entity {entity_identifier}")
                siemplify.LOGGER.exception(err)

            siemplify.LOGGER.info(f"Finish processing entity: {entity_identifier}")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )
            output_message = (
                f'Successfully updated agents based on the task "{task_name}" on the following '
                f"endpoints in {PRODUCT_NAME}: {', '.join(successful_entities)}\n"
            )

            if failed_entities:
                output_message += (
                    'Action wasn\'t able to update agent based on the task "{task_name}" on the '
                    f"following endpoints in {PRODUCT_NAME}: {', '.join(failed_entities)}"
                )
        else:
            output_message = "None of the agents were updated."
            result_value = False
    except Exception as err:
        result_value = False
        output_message = (
            f"Error executing action {UPDATE_MCAFEE_AGENT_SCRIPT_NAME}. Reason: {err}"
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

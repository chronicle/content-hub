from __future__ import annotations
from ..core.McAfeeCommon import McAfeeCommon
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import extract_configuration_param, flat_dict_to_csv
from ..core.constants import GET_AGENT_INFORMATION_SCRIPT_NAME, INTEGRATION_NAME, PRODUCT_NAME
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_AGENT_INFORMATION_SCRIPT_NAME
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
    status = EXECUTION_STATE_COMPLETED
    success_entities, failed_entities, entities_to_update, systems_data, json_result = (
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
            siemplify.LOGGER.info(f"Started processing entity: {entity}")
            entity_original_identifier = get_entity_original_identifier(entity)
            try:
                if manager.group:
                    McAfeeCommon.filter_systems_by_entity(systems_data, entity)

                system_info = manager.get_system_info(entity_original_identifier)
                agent_info = system_info.to_agent_info_json() if system_info else None

                if agent_info:
                    entity.additional_properties.update(
                        system_info.to_agent_enrichment_data()
                    )
                    entity.is_enriched = True
                    success_entities.append(entity_original_identifier)
                    entities_to_update.append(entity)
                    json_result[entity_original_identifier] = agent_info
                    siemplify.result.add_entity_table(
                        entity_original_identifier, flat_dict_to_csv(agent_info)
                    )
                else:
                    failed_entities.append(entity_original_identifier)

                siemplify.LOGGER.info(
                    f"Finished processing entity {entity_original_identifier}"
                )
            except Exception as e:
                failed_entities.append(entity_original_identifier)
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)
        if success_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )
            siemplify.update_entities(entities_to_update)
            output_message = (
                f"Successfully retrieved agent information about the following endpoints in "
                f'{PRODUCT_NAME}: {", ".join(success_entities)}\n'
            )
            if failed_entities:
                output_message += (
                    f"Action wasn't able to retrieve agent information about the following endpoints "
                    f'in {PRODUCT_NAME}: {", ".join(failed_entities)}\n'
                )
        else:
            result_value = False
            output_message = "No agent information was found for the provided hosts."

    except Exception as e:
        output_message = (
            f"Error executing action '{GET_AGENT_INFORMATION_SCRIPT_NAME}'. Reason: {e}"
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

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
from TIPCommon import (
    add_prefix_to_dict,
    extract_configuration_param,
    extract_action_param,
)
from ..core.constants import (
    PRODUCT_NAME,
    INTEGRATION_NAME,
    MCAFEE_EPO_PROVIDER_PREFIX,
    GET_SYSTEM_INFORMATION_SCRIPT_NAME,
    SYSTEM_INFORMATION_TABLE_NAME,
    SYSTEM_INFORMATION_INSIGHT_NAME,
)
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SYSTEM_INFORMATION_SCRIPT_NAME
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
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", input_type=bool
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, systems_data, result = [], [], [], {}
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

        if suitable_entities:
            systems_data = manager.get_systems_by_self_group()

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

            try:
                if manager.group:
                    filtered_system = McAfeeCommon.filter_systems_by_entity(
                        systems_data, entity
                    )
                    system = manager.get_system_information(filtered_system.parent_id)
                else:
                    system = manager.get_endpoint_system_info(entity_identifier)

                if system:
                    system.entity_identifier = entity_identifier
                    result[entity_identifier] = system
                    # Add enrichment data
                    enrichment_data = add_prefix_to_dict(
                        system.to_enrichment_data(), MCAFEE_EPO_PROVIDER_PREFIX
                    )
                    enrichment_data.update({"ThreatSource": INTEGRATION_NAME})
                    entity.additional_properties.update(enrichment_data)
                    successful_entities.append(entity)
            except Exception as err:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(f"Failed processing entity {entity_identifier}")
                siemplify.LOGGER.exception(err)

            siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(
                    {key: value.to_json() for key, value in result.items()}
                )
            )
            siemplify.result.add_data_table(
                SYSTEM_INFORMATION_TABLE_NAME,
                construct_csv([value.to_csv() for key, value in result.items()]),
            )
            siemplify.update_entities(successful_entities)
            if create_insight:
                siemplify.create_case_insight(
                    INTEGRATION_NAME,
                    SYSTEM_INFORMATION_INSIGHT_NAME,
                    construct_insight_view(result),
                    "",
                    0,
                    0,
                )
            output_message = (
                "Successfully retrieved system information about the following endpoints "
                f"from {PRODUCT_NAME}: "
                f"{', '.join([get_entity_original_identifier(entity) for entity in successful_entities])}\n"
            )

            if failed_entities:
                output_message += (
                    "Action wasn’t able to retrieve system information about the following endpoints "
                    f"from {PRODUCT_NAME}: {', '.join(failed_entities)}"
                )
        else:
            result_value = False
            output_message = (
                "No system information was found about the provided endpoints."
            )

    except Exception as err:
        result_value = False
        output_message = f"Error executing action {GET_SYSTEM_INFORMATION_SCRIPT_NAME}. Reason: {err}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def construct_insight_view(data):
    content = f"<p>Found information about {len(data.values())} endpoint{'s' if len(data.values()) > 1 else ''}.</p>"
    content += "".join([system.to_insight() for system in data.values()])

    return content


if __name__ == "__main__":
    main()

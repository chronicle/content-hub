from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.Siemplify import InsightSeverity, InsightType
from ..core.IvantiEndpointManagerManager import IvantiEndpointManagerManager
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.constants import (
    INTEGRATION_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
)

# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()
SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.MACADDRESS,
]
ENRICHMENT_PREFIX = "IvantiEndpointManager"
INSIGHT_TITLE = "General Info"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", print_value=True, input_type=bool
    )
    column_set = extract_action_param(
        siemplify, param_name="Custom Column Set", print_value=True
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    json_results = {}
    successful_entities, failed_entities = [], []
    successful_endpoints = []

    try:
        manager = IvantiEndpointManagerManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if column_set:
            if not manager.get_column_set_fields(
                column_set=column_set, filter_logic=None, filter_value=None, limit=None
            ):
                raise Exception(
                    f'column set "{column_set}" is invalid. '
                    f"Please check the spelling or remove it from the action configuration"
                )

        if suitable_entities:
            machines = manager.get_machines(entities=suitable_entities)

            if column_set:
                for machine in machines:
                    machine.machine_details = manager.get_machine_details(
                        guid=machine.guid, column_set=column_set
                    )

            if machines:
                for entity in suitable_entities:
                    siemplify.LOGGER.info(
                        f"Started processing entity: {entity.identifier}"
                    )
                    entity_details = next(
                        (
                            machine
                            for machine in machines
                            if entity.identifier
                            in [
                                machine.device_name,
                                machine.ip_address,
                                machine.mac_address,
                            ]
                        ),
                        None,
                    )
                    if entity_details:
                        json_results[entity.identifier] = entity_details.to_json()
                        entity.additional_properties.update(
                            entity_details.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                        )
                        successful_entities.append(entity)
                        successful_endpoints.append(entity_details.to_insight())
                        entity.is_enriched = True
                        siemplify.result.add_entity_table(
                            f"{entity.identifier}",
                            flat_dict_to_csv(entity_details.to_table()),
                        )
                    else:
                        failed_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )

        if successful_entities:
            output_message = (
                f"Successfully enriched the following entities using information from "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join([entity.identifier for entity in successful_entities])}\n"
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(successful_entities)

            if successful_endpoints and create_insight:
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_NAME,
                    title=INSIGHT_TITLE,
                    content="".join(successful_endpoints),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from "
                    f"{INTEGRATION_DISPLAY_NAME}: "
                    f"{', '.join([entity.identifier for entity in failed_entities])}"
                )
        else:
            output_message = "None of the provided entities were enriched."
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Enrich Entities". Reason: {e}.'
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

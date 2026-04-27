from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_action_param,
    dict_to_flat,
    add_prefix_to_dict,
    construct_csv,
)
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from ..core.manager_factory import create_qualys_manager_from_action
from ..core.constants import INTEGRATION_NAME, ENRICH_HOST_SCRIPT_NAME, ENRICHMENT_PREFIX
from soar_sdk.SiemplifyDataModel import EntityTypes

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_HOST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        is_mandatory=False,
        default_value=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    enriched_entities = []
    failed_entities = []
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        qualys_manager = create_qualys_manager_from_action(siemplify)
        qualys_manager.test_connectivity()
        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")

            try:
                if entity.entity_type == EntityTypes.ADDRESS:
                    host_details = qualys_manager.get_host_details(ip=entity.identifier)
                else:
                    host_details = qualys_manager.get_hostname_details(
                        hostname=entity.identifier
                    )

                if host_details:
                    json_results[entity.identifier] = host_details.to_json()
                    flat_host_details = dict_to_flat(host_details.to_enrichment_data())
                    # Enrich Entity
                    entity.additional_properties.update(
                        add_prefix_to_dict(flat_host_details, ENRICHMENT_PREFIX)
                    )
                    entity.is_enriched = True
                    enriched_entities.append(entity)
                    # Create Data Table
                    siemplify.result.add_entity_table(
                        entity.identifier, construct_csv(host_details.to_table())
                    )
                    if create_insight:
                        # Create Insight
                        siemplify.add_entity_insight(
                            entity,
                            message=host_details.as_insight(),
                            triggered_by=INTEGRATION_NAME,
                        )

                    siemplify.LOGGER.info(
                        f"Successfully processed entity {entity.identifier} and fetched details."
                    )
                else:
                    siemplify.LOGGER.info(
                        f"Successfully processed entity {entity.identifier} but no details were found in {INTEGRATION_NAME}."
                    )
                    failed_entities.append(entity)
            except Exception as e:
                # An error occurred - skip entity and continue
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        if enriched_entities:
            entities_names = [entity.identifier for entity in enriched_entities]
            output_message = "The following hosts were enriched:\n" + "\n".join(
                entities_names
            )
            siemplify.update_entities(enriched_entities)

            if failed_entities:
                output_message += (
                    f"\nAction wasn't able to enrich the following entities using information from "
                    f"{INTEGRATION_NAME}: "
                    f"{', '.join([entity.identifier for entity in failed_entities])}"
                )

        else:
            result = False
            output_message = "No hosts were enriched."

        # add json
        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ENRICH_HOST_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{ENRICH_HOST_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

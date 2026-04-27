from __future__ import annotations

from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes, DomainEntityInfo
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    flat_dict_to_csv,
    string_to_multi_value,
)
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
)
from ..core.datamodels import AgentResult, Endpoint
from ..core.UtilsManager import get_entity_original_identifier, process_agents


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


def get_entities_list(entities_list: list[DomainEntityInfo | str]) -> list[str]:
    """Get a list of entity identifiers from a list of entities.

    Args:
        entities_list (list[DomainEntityInfo | str]): The list of entities.

    Returns:
        list[str]: A list of entity identifiers.
    """
    entities = []
    for entity in entities_list:
        if isinstance(entity, DomainEntityInfo):
            entities.append(entity.identifier)
        elif isinstance(entity, Endpoint):
            entities.append(entity.guid)
        else:
            entities.append(entity)

    return entities


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
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    agent_uuids = string_to_multi_value(
        extract_action_param(
            siemplify,
            param_name="Agent UUID",
            print_value=True,
        )
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities, failed_entities = [], []
    json_result = {}

    try:
        manager = TrendVisionOneManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        manager.test_connectivity()

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
                if entity.entity_type == EntityTypes.ADDRESS:
                    endpoint = manager.search_endpoint(ip=entity_identifier)
                else:
                    endpoint = manager.search_endpoint(hostname=entity_identifier)

                if endpoint:
                    json_result[entity_identifier] = endpoint.to_json()
                    siemplify.LOGGER.info(f"Enriching entity {entity_identifier}")
                    entity.additional_properties.update(
                        endpoint.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                    )
                    entity.is_enriched = True
                    siemplify.result.add_entity_table(
                        entity_identifier, flat_dict_to_csv(endpoint.to_table())
                    )
                    successful_entities.append(entity)
                else:
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finish processing entity: {entity_identifier}")
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_identifier}."
                )
                siemplify.LOGGER.exception(e)

        agents: AgentResult = process_agents(
            manager=manager,
            agent_uids=agent_uuids,
        )
        successful_entities.extend(agents.successful_agents)
        failed_entities.extend(agents.failed_agents)
        if successful_entities:
            output_message += (
                f"Successfully enriched the following entities using information from "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join(get_entities_list(successful_entities))}\n\n"
            )
            siemplify.update_entities(
                [
                    entity
                    for entity in successful_entities
                    if isinstance(entity, DomainEntityInfo)
                ]
            )
            agent_json_result = {
                agent.guid: agent.to_json() for agent in agents.successful_agents
            }
            json_result.update(agent_json_result)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from"
                    f" {INTEGRATION_DISPLAY_NAME}: "
                    f"{', '.join(get_entities_list(failed_entities))}\n"
                )
        else:
            output_message = "None of the provided entities were enriched."
            result_value = False

    except Exception as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

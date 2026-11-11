from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from sentinel_one_v2.core.exceptions import SentinelOneV2NotFoundError
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import flat_dict_to_csv
from sentinel_one_v2.core.utils import get_entity_original_identifier
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    RECONNECT_AGENT_TO_THE_NETWORK_SCRIPT_NAME,
    UNSUCCESSFUL_ATTEMPTS_TABLE_NAME,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory

SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = RECONNECT_AGENT_TO_THE_NETWORK_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    success_entities, errors_dict = [], {}
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        sentinel_one_manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            try:
                siemplify.LOGGER.info(f"Processing entity {entity_identifier}")
                found_agent = None

                # Get endpoint agent id.
                if entity.entity_type == EntityTypes.HOSTNAME:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching agent for hostname {entity_identifier}"
                        )
                        found_agent = sentinel_one_manager.get_agent_by_hostname(
                            hostname=entity_identifier
                        )
                    except SentinelOneV2NotFoundError as e:
                        siemplify.LOGGER.info(e)
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")
                        continue

                elif entity.entity_type == EntityTypes.ADDRESS:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching agent for address {entity_identifier}"
                        )
                        found_agent = sentinel_one_manager.get_agent_by_ip(
                            ip_address=entity_identifier
                        )
                    except SentinelOneV2NotFoundError as e:
                        siemplify.LOGGER.info(e)
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")
                        continue

                if found_agent:
                    siemplify.LOGGER.info(
                        f"Found agent {found_agent.id} for entity {entity_identifier}"
                    )
                    siemplify.LOGGER.info(
                        f"Connecting agent {found_agent.id} from network."
                    )

                    if sentinel_one_manager.reconnect_agent_to_network(found_agent.id):
                        success_entities.append(entity_identifier)
                else:
                    siemplify.LOGGER.error(
                        f'Error: Not found id for entity "{entity_identifier}"'
                    )

            except Exception as e:
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)
                errors_dict[entity_identifier] = str(e)

        if success_entities:
            output_message = (
                "The following entities were reconnected to the network:"
                f"{', '.join(success_entities)}"
            )
        else:
            result_value = False
            output_message = "No target entities were reconnected from the network."

        # If were errors present them as a table.
        if errors_dict:
            siemplify.result.add_data_table(
                UNSUCCESSFUL_ATTEMPTS_TABLE_NAME, flat_dict_to_csv(errors_dict)
            )

    except Exception as e:
        output_message = (
            f"Error executing action '{RECONNECT_AGENT_TO_THE_NETWORK_SCRIPT_NAME}'."
            "Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n"
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

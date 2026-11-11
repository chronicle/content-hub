from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from sentinel_one_v2.core.exceptions import SentinelOneV2NotFoundError
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import flat_dict_to_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    INITIATE_FULL_SCAN_SCRIPT_NAME,
    PRODUCT_NAME,
    UNSUCCESSFUL_ATTEMPTS_TABLE_NAME,
)
from sentinel_one_v2.core.utils import get_entity_original_identifier
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory

SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INITIATE_FULL_SCAN_SCRIPT_NAME

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

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities = [], []
    errors_dict = {}

    try:
        sentinel_one_manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for entity in scope_entities:
            entity_identifier = get_entity_original_identifier(entity)
            try:
                siemplify.LOGGER.info(f"Processing entity {entity_identifier}")
                agent = None
                if entity.entity_type == EntityTypes.HOSTNAME:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching agent for hostname {entity_identifier}"
                        )
                        agent = sentinel_one_manager.get_agent_by_hostname(
                            hostname=entity_identifier
                        )
                    except SentinelOneV2NotFoundError as e:
                        failed_entities.append(entity_identifier)
                        siemplify.LOGGER.info(e)
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")
                        continue

                if entity.entity_type == EntityTypes.ADDRESS:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching agent for address {entity_identifier}"
                        )
                        agent = sentinel_one_manager.get_agent_by_ip(
                            ip_address=entity_identifier
                        )
                    except SentinelOneV2NotFoundError as e:
                        failed_entities.append(entity_identifier)
                        siemplify.LOGGER.info(e)
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")
                        continue

                if agent and agent.uuid:
                    siemplify.LOGGER.info(
                        f"Found agent {agent.uuid} for entity {entity_identifier}"
                    )
                    siemplify.LOGGER.info(
                        f"Initiating full scan for agent {agent.uuid}"
                    )
                    sentinel_one_manager.initiate_full_scan_by_uuid(agent.uuid)
                    successful_entities.append(entity_identifier)
                else:
                    siemplify.LOGGER.error(
                        f'Error: Not found uuid for entity "{entity_identifier}"'
                    )
            except Exception as err:
                failed_entities.append(entity_identifier)
                errors_dict[entity_identifier] = str(err)
                siemplify.LOGGER.error(
                    f"An error occurred on the {entity_identifier} entity: {err}"
                )
                siemplify.LOGGER.exception(err)

        if errors_dict:
            siemplify.result.add_data_table(
                UNSUCCESSFUL_ATTEMPTS_TABLE_NAME, flat_dict_to_csv(errors_dict)
            )

        if successful_entities:
            output_message = (
                f"Successfully started the full disk scan on the following"
                f"endpoints in {PRODUCT_NAME}:{', '.join(successful_entities)}"
                "\n"
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to start a full disk scan on the following"
                    f"endpoints in {PRODUCT_NAME}: {', '.join(failed_entities)}\n"
                )

        else:
            output_message = "No full disk scans were initiated."
            result_value = False

    except Exception as err:
        output_message = (
            f"Error executing action '{INITIATE_FULL_SCAN_SCRIPT_NAME}'. Reason: {err}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
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

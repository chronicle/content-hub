from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.ForeScoutCounterACTManager import ForeScoutCounterACTManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.Siemplify import InsightSeverity, InsightType
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
    construct_csv,
)
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
)

# Fix of misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.lower()
SUPPORTED_ENTITIES = [EntityTypes.MACADDRESS, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration configuration
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
        print_value=False,
        remove_whitespaces=False,
    )
    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=True,
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Action results
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_results = {}

    # Processing
    successful_entities = []
    failed_entities = []

    try:
        manager = ForeScoutCounterACTManager(
            api_root=api_root,
            username=username,
            password=password,
            ca_certificate_file=ca_certificate_file,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        supported_entities = [
            entity
            for entity in siemplify.target_entities
            if (entity.entity_type in SUPPORTED_ENTITIES)
            or (entity.entity_type.lower() == EntityTypes.MACADDRESS)
        ]

        for entity in supported_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                entity_identifier = entity.identifier
                entity_details = None
                if entity.entity_type.lower() == EntityTypes.MACADDRESS:
                    entity_identifier = entity_identifier.replace(":", "")
                    entity_details = manager.get_endpoint_info_by_mac(
                        mac_address=entity_identifier
                    )
                elif entity.entity_type == EntityTypes.ADDRESS:
                    entity_details = manager.get_endpoint_info_by_ip_address(
                        ip_address=entity_identifier
                    )

                if not entity_details:
                    siemplify.LOGGER.error("No entity details were found")
                    failed_entities.append(entity)
                    continue

                if create_insight:
                    siemplify.create_case_insight(
                        triggered_by=INTEGRATION_NAME,
                        title=entity.identifier,
                        content=entity_details.to_insight(entity.identifier),
                        entity_identifier=entity.identifier,
                        severity=InsightSeverity.INFO,
                        insight_type=InsightType.Entity,
                    )
                json_results[entity.identifier] = entity_details.to_json()
                entity.additional_properties.update(entity_details.to_enrichment())
                entity.is_enriched = True
                siemplify.result.add_entity_table(
                    entity.identifier, data_table=construct_csv(entity_details.to_csv())
                )
                successful_entities.append(entity)
                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")
            except Exception as error:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(error)

        if successful_entities:
            output_message += (
                "Successfully enriched the following entities using {}:\n   {}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n   ".join([entity.identifier for entity in successful_entities]),
                )
            )
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            result_value = True
            if failed_entities:
                output_message += "\n\nAction wasn't able to enrich the following entities using {}:\n   {}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n   ".join([entity.identifier for entity in failed_entities]),
                )
        else:
            output_message += "No entities were enriched"

    except Exception as error:
        output_message = (
            f'Error executing action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

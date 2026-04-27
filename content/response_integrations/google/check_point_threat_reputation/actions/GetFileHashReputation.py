from __future__ import annotations
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    add_prefix_to_dict,
    construct_csv,
)

from ..core.CheckPointThreatReputationManager import CheckPointThreatReputationManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from ..core.constants import (
    INTEGRATION_NAME,
    ENTITY_ENRICHMENT_PREFIX,
    ENTITY_TABLE_NAME,
    WHITE_LIST_CLASSIFICATION,
)

SCRIPT_NAME = "CheckPoint Threat Reputation - GetFileHashReputation"
SUPPORTED_ENTITIES = EntityTypes.FILEHASH


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        default_value=True,
        input_type=bool,
    )

    threshold = extract_action_param(
        siemplify,
        param_name="Threshold",
        is_mandatory=True,
        print_value=True,
        input_type=int,
        default_value=0,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight?",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    enriched_entities = []  # successfully enriched entities
    failed_entities = []  # failed enriched entities

    json_results = {}
    output_message = ""
    result_value = "true"

    try:
        siemplify.LOGGER.info("Connecting to CheckPoint Threat Reputation service")
        manager = CheckPointThreatReputationManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Connected successfully to CheckPoint Reputation service")

        for entity in siemplify.target_entities:

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is not supported. Skipping entity.."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                siemplify.LOGGER.info(
                    f"Fetching entity {entity.identifier} reputation data"
                )
                file_reputation = manager.get_file_hash_reputation(
                    entity.identifier
                )  # Reputation Model
                siemplify.LOGGER.info(
                    f"Successfully fetched data for entity {entity.identifier}"
                )

                if (
                    file_reputation.risk > threshold
                    and file_reputation.reputation_classification.classification
                    not in WHITE_LIST_CLASSIFICATION
                ):
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} found to be suspicious"
                    )
                    entity.is_suspicious = True
                else:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} found NOT to be suspicious"
                    )
                    entity.is_suspicious = False

                if create_insight:
                    siemplify.LOGGER.info(
                        f"Creating insight for entity {entity.identifier}"
                    )
                    siemplify.add_entity_insight(
                        entity,
                        message=file_reputation.as_insight(),
                        triggered_by=INTEGRATION_NAME,
                    )

                prefixed_file_reputation = add_prefix_to_dict(
                    file_reputation.enriched_data_to_flatted_dict(),
                    ENTITY_ENRICHMENT_PREFIX,
                )

                entity.additional_properties.update(prefixed_file_reputation)

                json_results[entity.identifier] = (
                    file_reputation.raw_response_without_status
                )

                siemplify.LOGGER.info(
                    f"Creating csv table for entity {entity.identifier}"
                )

                siemplify.result.add_data_table(
                    f"{ENTITY_TABLE_NAME} results for {entity.identifier}",
                    construct_csv([file_reputation.to_csv()]),
                )
                entity.is_enriched = True
                enriched_entities.append(entity)  # append successfull entity
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if enriched_entities:  # if at least one of the entities got enriched
            output_message += "Successfully enriched entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in enriched_entities])
            )
            siemplify.update_entities(enriched_entities)
        else:  # failed to enrich all provided entities
            result_value = "false"
            output_message += "No entities were enriched."

        if failed_entities:  # failed to find data to enrich specific entities
            output_message += "Action was not able to find CheckPoint Threat Reputation info to enrich the following entities: \n{}\n".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to connect to the CheckPoint Threat Reputation service! Error is {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to connect to the CheckPoint Threat Reputation service! Error is {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

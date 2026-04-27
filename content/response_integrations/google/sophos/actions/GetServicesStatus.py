from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.SophosManager import SophosManager
from TIPCommon import extract_configuration_param, construct_csv
from ..core.constants import INTEGRATION_NAME, GET_SERVICE_STATUS_SCRIPT_NAME
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SERVICE_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = SophosManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            test_connectivity=True,
        )

        status = EXECUTION_STATE_COMPLETED
        successful_entities, failed_entities, csv_output, json_results = [], [], [], {}
        output_message = ""
        result_value = True
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITIES
        ]

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            entity_type = entity.entity_type
            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                endpoint = manager.find_entities(
                    entity_identifier=entity_identifier, entity_type=entity_type
                )
                if not endpoint:
                    failed_entities.append(entity_identifier)
                    continue
                json_results[entity_identifier] = endpoint.to_json()
                csv_output = [
                    service_detail.to_csv()
                    for service_detail in endpoint.service_details
                ]
                siemplify.result.add_entity_table(
                    entity.identifier, construct_csv(csv_output)
                )
                successful_entities.append(entity_identifier)

            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
        if successful_entities:
            output_message += (
                "Successfully retrieved service information from the following "
                f"entities in {INTEGRATION_NAME}: {', '.join(successful_entities)}"
            )

            if failed_entities:
                output_message += f"\nThe following entities were not found in {INTEGRATION_NAME}: {', '.join(failed_entities)}"

        else:
            output_message += (
                f"None of the provided entities were found in {INTEGRATION_NAME}."
            )
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {GET_SERVICE_STATUS_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

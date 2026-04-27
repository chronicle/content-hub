from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.SophosManager import SophosManager
from TIPCommon import extract_configuration_param
from ..core.constants import INTEGRATION_NAME, SCAN_ENDPOINTS_SCRIPT_NAME
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCAN_ENDPOINTS_SCRIPT_NAME
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
        successful_entities, failed_entities = [], []
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
                    siemplify.LOGGER.info(
                        f"Endpoint was not found for entity {entity_identifier}. "
                        "Skipping."
                    )
                    failed_entities.append(entity_identifier)
                    continue
                manager.scan_endpoint(scan_id=endpoint.scan_id)
                successful_entities.append(entity_identifier)
                siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = (
                "Successfully initiated scan on the following entities in {}:"
                "\n   {}".format(INTEGRATION_NAME, ", ".join(successful_entities))
            )

            if failed_entities:
                output_message += (
                    "\nThe following entities were not found in {}:"
                    "\n   {}".format(INTEGRATION_NAME, ", ".join(failed_entities))
                )

        else:
            output_message = (
                f"None of the provided entities were found in {INTEGRATION_NAME}."
            )
            result_value = False

    except Exception as e:
        siemplify.LOGGER.error(
            f"Error executing action {SCAN_ENDPOINTS_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f"Error executing action {SCAN_ENDPOINTS_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

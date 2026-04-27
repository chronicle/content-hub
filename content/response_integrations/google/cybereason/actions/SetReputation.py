from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.CybereasonManager import CybereasonManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    SET_REPUTATION_SCRIPT_NAME,
    SUPPORTED_FILE_HASH_TYPES,
    WHITELIST,
)
from ..core.utils import get_entity_original_identifier, get_domain_from_entity, get_hash_type

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.URL, EntityTypes.FILEHASH]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SET_REPUTATION_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
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
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate Base64",
    )

    list_type = extract_action_param(
        siemplify,
        param_name="Reputation List Type",
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            force_check_connectivity=True,
        )

        status = EXECUTION_STATE_COMPLETED
        successful_entities, failed_entities = [], []
        result_value = True
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                entity_identifier_for_api = (
                    entity_identifier
                    if entity.entity_type != EntityTypes.URL
                    else get_domain_from_entity(entity_identifier)
                )

                siemplify.LOGGER.info(
                    f"Setting reputation for hash {entity_identifier}"
                )
                if entity.entity_type == EntityTypes.FILEHASH:
                    if (
                        get_hash_type(entity_identifier)
                        not in SUPPORTED_FILE_HASH_TYPES
                    ):
                        failed_entities.append(entity_identifier)
                        siemplify.LOGGER.info(
                            f"Hash {entity_identifier} is not supported. Supported types are MD5, SHA1"
                        )
                        continue

                manager.set_custom_reputation(
                    entity_identifier_for_api, whitelist=list_type == WHITELIST
                )

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
                f'Successfully set "{list_type}" reputation for the following entities: '
                f'{", ".join(successful_entities)}\n'
            )
            if failed_entities:
                output_message += (
                    f"Action wasn't able to set reputation for the following entities: "
                    f'{", ".join(failed_entities)}\n'
                )
        else:
            result_value = False
            output_message = f"Reputation was not set for the provided entities."

    except Exception as e:
        output_message = (
            f"Error executing action {SET_REPUTATION_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

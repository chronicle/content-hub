from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.CylanceManager import CylanceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    PROVIDER_NAME,
    GET_THREAT_DOWNLOAD_LINK,
    PARAMETERS_DEFAULT_DELIMITER,
    ENRICH_PREFIX,
)
from soar_sdk.SiemplifyDataModel import EntityTypes


# Constants
SUPPORTED_ENTITY_TYPES = [EntityTypes.FILEHASH]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_THREAT_DOWNLOAD_LINK
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    server_address = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Server Address",
        is_mandatory=True,
        print_value=True,
    )
    application_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Application ID",
        is_mandatory=True,
        print_value=True,
    )
    application_secret = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Application Secret",
        is_mandatory=True,
    )
    tenant_identifier = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Tenant Identifier",
        is_mandatory=True,
    )

    threat_hashes = extract_action_param(
        siemplify, param_name="Threat SHA256 Hash", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_messages = ""
    json_results = {}
    successful_entities = []
    failed_entities = []

    try:
        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]
        hashes_list = (
            [
                threat_hash.strip()
                for threat_hash in threat_hashes.split(PARAMETERS_DEFAULT_DELIMITER)
                if threat_hash.strip()
            ]
            if threat_hashes
            else []
        )

        # Create manager instance
        manager = CylanceManager(
            server_address, application_id, application_secret, tenant_identifier
        )

        if hashes_list or target_entities:
            target_hashes = (
                hashes_list
                if hashes_list
                else [entity.identifier for entity in target_entities]
            )

            for target_hash in target_hashes:
                siemplify.LOGGER.info(f"\n\nStarted processing hash: {target_hash}")
                try:
                    result = manager.get_threat_download_link(target_hash)
                    json_results[target_hash] = result.to_json()
                    successful_entities.append(target_hash)

                    if not hashes_list:
                        entity = next(
                            entity
                            for entity in target_entities
                            if entity.identifier == target_hash
                        )
                        enrichment_data = result.to_enrichment_data(
                            prefix=ENRICH_PREFIX
                        )
                        entity.additional_properties.update(enrichment_data)
                        entity.is_enriched = True
                except Exception as e:
                    failed_entities.append(target_hash)
                    siemplify.LOGGER.error(f"Failed processing hash: {target_hash}")
                    siemplify.LOGGER.error(e)

                siemplify.LOGGER.info(f"Finished processing hash {target_hash}")

        if successful_entities:
            if not hashes_list:
                siemplify.update_entities(
                    [
                        entity
                        for entity in target_entities
                        if entity.identifier in successful_entities
                    ]
                )

            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_messages += (
                "Successfully fetched download link for following hashes: \n{}".format(
                    "\n".join([entity for entity in successful_entities])
                )
            )

        if failed_entities:
            output_messages += "\nAction could not fetch download link for following hashes: \n{}".format(
                "\n".join([entity for entity in failed_entities])
            )

        if not successful_entities:
            output_messages = "No download links were fetched"
            result_value = False

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {GET_THREAT_DOWNLOAD_LINK}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_messages = (
            f'Error executing action "Get Threat Download Link". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Messages: {output_messages}")

    siemplify.end(output_messages, result_value, status)


if __name__ == "__main__":
    main()

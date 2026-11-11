from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from symantec_escc.core.UtilsManager import convert_comma_separated_to_list
from symantec_escc.core.SymantecESCCManager import SymantecESCCManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from symantec_escc.core.constants import INTEGRATION_NAME, GET_RELATED_IOCS_ACTION, FILE_IOC, DOMAIN_IOC

SUPPORTED_ENTITY_TYPES = [EntityTypes.URL, EntityTypes.FILEHASH, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RELATED_IOCS_ACTION

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    source_filter = extract_action_param(
        siemplify, param_name="Source Filter", print_value=True
    )

    source_filter = convert_comma_separated_to_list(source_filter)

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    file_iocs, domain_iocs, ip_iocs = [], [], []

    try:
        manager = SymantecESCCManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            if (
                entity.entity_type == EntityTypes.FILEHASH
                and len(entity.identifier) != 64
            ):
                siemplify.LOGGER.info(
                    f"Hash {entity.identifier} is not of type sha256. Skipping."
                )
                continue

            related_iocs = manager.get_related_iocs(entity)
            related_iocs = [
                ioc for ioc in related_iocs if ioc.relation in source_filter
            ]
            for ioc in related_iocs:
                if ioc.ioc_type == FILE_IOC:
                    file_iocs.extend(ioc.ioc_values)
                elif ioc.ioc_type == DOMAIN_IOC:
                    domain_iocs.extend(ioc.ioc_values)
                else:
                    ip_iocs.extend(ioc.ioc_values)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        json_result = {
            "total_file_IOCs": list(set(file_iocs)),
            "total_domain_IOCs": list(set(domain_iocs)),
            "total_IP_IOCs": list(set(ip_iocs)),
        }

        if file_iocs or domain_iocs or ip_iocs:
            output_message = f"Successfully returned related IOCs for the provided entities from {INTEGRATION_NAME}."
            siemplify.result.add_result_json(json_result)
        else:
            output_message = f"No related IOCs were found for the provided entities from {INTEGRATION_NAME}."
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Get Related IOCs". Reason: {e}.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

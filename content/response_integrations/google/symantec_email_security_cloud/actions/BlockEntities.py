from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.SymantecEmailSecurityCloudManager import SymantecEmailSecurityCloudManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    BLOCK_ENTITIES_SCRIPT_NAME,
    IOC_TYPES_MAPPING,
    REMEDIATION_MAPPING,
    DEFAULT_REMEDIATION,
    SHA256_LENGTH,
    MD5_LENGTH,
)
from ..core.UtilsManager import is_valid_email, get_entity_original_identifier


SUPPORTED_ENTITIES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.USER,
    EntityTypes.URL,
    EntityTypes.FILEHASH,
    EntityTypes.EMAILMESSAGE,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = BLOCK_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="IOC API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
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
        input_type=bool,
        print_value=True,
    )

    # action parameters
    remediation_action = extract_action_param(
        siemplify,
        param_name="Remediation Action",
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_REMEDIATION,
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    entity_ioc_dict = {}
    successful_entities = []
    failed_entities = []
    json_results = {}
    output_message = ""
    result_value = True

    try:
        manager = SymantecEmailSecurityCloudManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for entity in siemplify.target_entities:
            entity_identifier = get_entity_original_identifier(entity)
            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            if entity.entity_type == EntityTypes.FILEHASH:
                if len(entity_identifier) not in [SHA256_LENGTH, MD5_LENGTH]:
                    siemplify.LOGGER.error(
                        "Not supported hash type. Provide either MD5 or SHA-256."
                    )
                    continue

                hash_type = "MD5" if len(entity_identifier) == MD5_LENGTH else "SHA256"
                entity_ioc_dict[entity_identifier] = IOC_TYPES_MAPPING.get(
                    entity.entity_type
                ).get(hash_type)
            elif entity.entity_type == EntityTypes.USER:
                if is_valid_email(entity_identifier):
                    entity_ioc_dict[entity_identifier] = IOC_TYPES_MAPPING.get(
                        entity.entity_type
                    )
            else:
                entity_ioc_dict[entity_identifier] = IOC_TYPES_MAPPING.get(
                    entity.entity_type
                )
            siemplify.LOGGER.info(f"Finished processing entity: {entity_identifier}")

        ioc_results = manager.block_iocs(
            iocs_dict=entity_ioc_dict,
            remediation_action=REMEDIATION_MAPPING.get(remediation_action),
            description=description,
        )

        for identifier, data in entity_ioc_dict.items():
            ioc_res = next(
                (res for res in ioc_results if res.ioc_value == identifier), None
            )
            if ioc_res:
                failed_entities.append(identifier)
                json_results[identifier] = {
                    "status": "Failure",
                    "reason": ioc_res.failure_reason,
                }
            else:
                successful_entities.append(identifier)
                json_results[identifier] = {"status": "Success"}

        if successful_entities:
            output_message += (
                "Successfully blocked the following entities in {}:\n{}\n\n".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity for entity in successful_entities]),
                )
            )

        if failed_entities:
            output_message += (
                "Action wasn't able to block the following entities in {}:\n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity for entity in failed_entities]),
                )
            )

        if not successful_entities:
            result_value = False
            output_message = "None of the provided entities were blocked."

        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    except Exception as e:
        siemplify.LOGGER.error(
            f'Error executing action "{BLOCK_ENTITIES_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f'Error executing action "{BLOCK_ENTITIES_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

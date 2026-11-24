from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from sentinel_one_v2.core.constants import (
    CREATE_HASH_EXCLUSION_RECORD_SCRIPT_NAME,
    INTEGRATION_NAME,
    PRODUCT_NAME,
)
from sentinel_one_v2.core.exceptions import (
    SentinelOneV2ValidationError,
    SentinelOneV2AlreadyExistsError,
    SentinelOneV2PermissionError,
)
from sentinel_one_v2.core.utils import get_entity_original_identifier
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_HASH_EXCLUSION_RECORD_SCRIPT_NAME
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

    operation_system = extract_action_param(
        siemplify, param_name="Operation System", is_mandatory=True, print_value=True
    )

    site_ids = extract_action_param(siemplify, param_name="Site IDs", print_value=True)
    group_ids = extract_action_param(
        siemplify, param_name="Group IDs", print_value=True
    )
    account_ids = extract_action_param(
        siemplify, param_name="Account IDs", print_value=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", print_value=True
    )
    add_to_global_list = extract_action_param(
        siemplify,
        param_name="Add to global exclusion list",
        input_type=bool,
        print_value=True,
    )
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.FILEHASH
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, exists_entities = [], [], []
    json_results = {}

    try:
        if (
            not site_ids
            and not group_ids
            and not account_ids
            and not add_to_global_list
        ):
            raise SentinelOneV2ValidationError(
                'at least one value should be provided for "Site IDs" or "Group IDs" or "Account IDs" parameters '
                'or "Add to global exclusion list" should be enabled.'
            )

        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        for entity in suitable_entities:
            entity_original_identifier = get_entity_original_identifier(entity)
            siemplify.LOGGER.info(
                f"Started processing entity: {entity_original_identifier}"
            )
            try:
                results = manager.create_hash_exclusion(
                    hash_value=entity_original_identifier,
                    os_type=operation_system,
                    site_ids=site_ids,
                    group_ids=group_ids,
                    account_ids=account_ids,
                    description=description,
                    tenant=add_to_global_list,
                )
                json_results[entity_original_identifier] = [
                    result.to_json() for result in results
                ]
                successful_entities.append(entity_original_identifier)

            except SentinelOneV2AlreadyExistsError as err:
                siemplify.LOGGER.error(
                    f"Already exists for entity: {entity_original_identifier}: {err}"
                )
                siemplify.LOGGER.exception(err)
                exists_entities.append(entity_original_identifier)
            except Exception as err:
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_original_identifier}: {err}"
                )
                siemplify.LOGGER.exception(err)
                failed_entities.append(entity_original_identifier)
                if isinstance(err, SentinelOneV2PermissionError):
                    raise

            siemplify.LOGGER.info(
                f"Finished processing entity: {entity_original_identifier}."
            )

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message = "Successfully added the following hashes to the exclusion list in {}: \n {}\n".format(
                PRODUCT_NAME, "\n".join(successful_entities)
            )

        if exists_entities:
            output_message += "The following hashes were already a part of exclusion in {}: \n{}\n".format(
                PRODUCT_NAME, "\n".join(exists_entities)
            )

        if failed_entities:
            output_message += "Action wasn't able to add the following hashes to the exclusion list in {}: \n{}\n".format(
                PRODUCT_NAME, "\n".join(failed_entities)
            )

        if not successful_entities and not exists_entities:
            output_message = (
                f"No hashes were added to the exclusion list in {PRODUCT_NAME}"
            )
            result_value = False

    except Exception as err:
        output_message = f"Error executing action '{CREATE_HASH_EXCLUSION_RECORD_SCRIPT_NAME}'. Reason: {err}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

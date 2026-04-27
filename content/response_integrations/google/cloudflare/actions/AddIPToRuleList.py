from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.CloudflareManager import CloudflareManager

from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ADD_IP_TO_RULE_LIST_SCRIPT_NAME,
    SUITABLE_RULE_LIST_KIND,
)
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_IP_TO_RULE_LIST_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    account_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Account Name"
    )

    # action parameter
    name = extract_action_param(
        siemplify, param_name="Rule Name", is_mandatory=True, print_value=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities = [], []
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    result_value = True

    try:
        manager = CloudflareManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            account_name=account_name,
            siemplify_logger=siemplify.LOGGER,
        )
        rule_list_object = manager.get_rule_list(name)
        if rule_list_object.kind != SUITABLE_RULE_LIST_KIND:
            raise Exception(
                f"Error executing action {ADD_IP_TO_RULE_LIST_SCRIPT_NAME}. "
                f"Reason: rule list {name} is not of a type 'IP'."
            )
        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")
            entity_identifier = get_entity_original_identifier(entity)
            try:
                data = manager.add_ip_to_rule_list(
                    rule_list_object.rule_list_id, description, entity_identifier
                )
                json_results[entity_identifier] = data.to_json()
                successful_entities.append(entity)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Action wasn't able to add the following entity to the {name}"
                    f" rule list in {INTEGRATION_DISPLAY_NAME}: {entity.identifier}. Reason: {e}"
                )
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")
        output_message = ""
        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += "Successfully added the following IPs to the {} IP Address Range in {}: \n {}".format(
                name,
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )
        if failed_entities:
            output_message += "\nAction wasn't able to add the following IPs to the {} IP Address Range in {}: \n {}".format(
                name,
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )
        if not successful_entities:
            result_value = False
            output_message = f"None of the IPs were added to the IP Address Range in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ADD_IP_TO_RULE_LIST_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f'Error executing action "{ADD_IP_TO_RULE_LIST_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

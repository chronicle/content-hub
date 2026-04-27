from __future__ import annotations
from typing import Dict, List, Tuple
from ..core.CloudflareManager import CloudflareManager
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    ADD_URL_TO_RULE_LIST_SCRIPT_NAME,
    INTEGRATION_NAME,
    ADD_URL_TO_RULE_LIST_SUITABLE_RULE_LIST_KIND,
)


def process_entities(
    siemplify: SiemplifyAction,
    manager: CloudflareManager,
    rule_list_id: str,
    rule_list_item_payload: Dict,
) -> Tuple[List, List, dict]:
    """
    Iterates over suitable entities and adds a Rule List Item to each of them

    Args:
        siemplify: Siemplify Action object
        manager: Cloudflare Manager object
        rule_list_id: ID of target Rule List
        rule_list_item_payload: Information about new Rule List Item

    Returns:
        Two lists and one dict, first with failed entities, second with successful ones, third with json result
    """
    failed_entities = []
    successful_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.URL:
            try:
                siemplify.LOGGER.info(
                    f"\nStarted processing entity: {entity.identifier}"
                )

                rule = manager.add_url_to_rule_list(
                    rule_list_id,
                    {**rule_list_item_payload, "source_url": entity.identifier},
                )

                json_results[entity.identifier] = rule.to_json()
                successful_entities.append(entity)

            except Exception as error:
                siemplify.LOGGER.error(
                    f"Failed processing entities: {entity.identifier}: Error is: {error}"
                )
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

    return failed_entities, successful_entities, json_results


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_URL_TO_RULE_LIST_SCRIPT_NAME
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
    account_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account Name",
        is_mandatory=True,
        remove_whitespaces=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    rule_name = extract_action_param(
        siemplify, param_name="Rule Name", is_mandatory=True, input_type=str
    )
    target_url = extract_action_param(
        siemplify, param_name="Target URL", is_mandatory=True, input_type=str
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, input_type=str
    )
    status_code = extract_action_param(
        siemplify, param_name="Status Code", is_mandatory=False, input_type=int
    )
    preserve_query_string = extract_action_param(
        siemplify,
        param_name="Preserve Query String",
        is_mandatory=False,
        input_type=bool,
    )
    include_subdomains = extract_action_param(
        siemplify, param_name="Include Subdomains", is_mandatory=False, input_type=bool
    )
    subpath_matching = extract_action_param(
        siemplify, param_name="Subpath Matching", is_mandatory=False, input_type=bool
    )
    preserve_path_suffix = extract_action_param(
        siemplify,
        param_name="Preserve Path Suffix",
        is_mandatory=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if preserve_path_suffix and not subpath_matching:
            raise Exception(
                'you need to enable "Subpath Matching", if "Preserve Path Suffix" is enabled'
            )

        rule_list_item_payload = {
            "target_url": target_url,
            "comment": description,
            "status_code": status_code,
            "preserve_query_string": preserve_query_string,
            "include_subdomains": include_subdomains,
            "subpath_matching": subpath_matching,
            "preserve_path_suffix": preserve_path_suffix,
        }

        result = True
        output_message = ""
        status = EXECUTION_STATE_COMPLETED

        manager = CloudflareManager(
            api_root=api_root,
            api_token=api_token,
            account_name=account_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        rule_list = manager.get_rule_list(rule_name)

        if rule_list.kind != ADD_URL_TO_RULE_LIST_SUITABLE_RULE_LIST_KIND:
            raise Exception(
                f'Error executing action "{ADD_URL_TO_RULE_LIST_SCRIPT_NAME}". Reason: rule list {rule_name} '
                f'is not of type "{ADD_URL_TO_RULE_LIST_SUITABLE_RULE_LIST_KIND.capitalize()}".'
            )

        failed_entities, successful_entities, json_results = process_entities(
            siemplify, manager, rule_list.rule_list_id, rule_list_item_payload
        )

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += (
                f"Successfully added the following entities "
                f"to the {rule_name} rule list in {INTEGRATION_NAME}: "
                f"{','.join(entity.identifier for entity in successful_entities)}\n"
            )
        if failed_entities:
            output_message += (
                f"Action wasn't able to add the following entities "
                f"to the {rule_name} rule list in {INTEGRATION_NAME}: "
                f"{','.join(entity.identifier for entity in failed_entities)}\n"
            )

        if not successful_entities:
            result = False
            output_message = f"None of the provided entities were added to the {rule_name} rule list."

    except Exception as error:
        output_message = (
            f"Error executing action {ADD_URL_TO_RULE_LIST_SCRIPT_NAME}. "
            f"Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

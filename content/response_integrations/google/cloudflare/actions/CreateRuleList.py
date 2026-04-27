from __future__ import annotations
from ..core.CloudflareManager import CloudflareManager
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    CREATE_RULE_LIST_SCRIPT_NAME,
    INTEGRATION_NAME,
    RULE_LIST_TYPE_MAPPING,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_RULE_LIST_SCRIPT_NAME
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
        remove_whitespaces=False,
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

    name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, input_type=str
    )
    rule_list_type = extract_action_param(
        siemplify, param_name="Type", is_mandatory=False, input_type=str
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, input_type=str
    )
    rule_list_type = RULE_LIST_TYPE_MAPPING.get(rule_list_type)
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        manager = CloudflareManager(
            api_root=api_root,
            api_token=api_token,
            account_name=account_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        rule_list_object = manager.create_rule_list(name, rule_list_type, description)
        siemplify.result.add_result_json(rule_list_object.to_json())
        status = EXECUTION_STATE_COMPLETED
        result = True
        output_message = "Successfully create a rule list in Cloudflare."
    except Exception as error:
        output_message = (
            f"Error executing action {CREATE_RULE_LIST_SCRIPT_NAME}. Reason: {error}"
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

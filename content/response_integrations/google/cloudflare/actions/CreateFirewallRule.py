from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.CloudflareManager import CloudflareManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.UtilsManager import convert_comma_separated_to_list, convert_list_to_comma_string
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    CREATE_FIREWALL_RULE_SCRIPT_NAME,
    RULE_ACTION_MAPPING,
    RULE_PRODUCTS_POSSIBLE_VALUES,
    CHARACTERS_MAX_LIMIT,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_FIREWALL_RULE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # integration configuration
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

    zone_name = extract_action_param(
        siemplify, param_name="Zone Name", is_mandatory=True, print_value=True
    )
    name = extract_action_param(siemplify, param_name="Name", print_value=True)
    action = extract_action_param(siemplify, param_name="Action", print_value=True)
    expression = extract_action_param(
        siemplify, param_name="Expression", is_mandatory=True, print_value=True
    )
    products = extract_action_param(siemplify, param_name="Products", print_value=True)
    priority = extract_action_param(
        siemplify, param_name="Priority", input_type=int, print_value=True
    )
    reference_tag = extract_action_param(
        siemplify, param_name="Reference Tag", print_value=True
    )

    products = convert_comma_separated_to_list(products)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if list(set(products) - set(RULE_PRODUCTS_POSSIBLE_VALUES)):
            raise Exception(
                f'Invalid value provided in the "Products" parameter. Possible values: '
                f"{convert_list_to_comma_string(RULE_PRODUCTS_POSSIBLE_VALUES)}"
            )

        if RULE_ACTION_MAPPING.get(action) == "bypass" and not products:
            raise Exception(
                '"Products" should be provided, when "Bypass" is selected in "Action" parameter'
            )

        if reference_tag and len(reference_tag) > CHARACTERS_MAX_LIMIT:
            raise Exception(
                f'"Reference Tag" can only be up to {CHARACTERS_MAX_LIMIT} characters long'
            )

        if priority and priority < 0:
            raise Exception(
                f'Invalid value was provided for "Priority": {priority}. Positive number '
                f"should be provided."
            )

        manager = CloudflareManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            account_name=account_name,
            siemplify_logger=siemplify.LOGGER,
        )

        zone = manager.get_zone(zone_name=zone_name)

        if not zone:
            raise Exception(
                f"zone {zone_name} wasn't found in {INTEGRATION_DISPLAY_NAME}."
            )

        rules = manager.create_firewall_rule(
            zone_id=zone.zone_id,
            action=RULE_ACTION_MAPPING.get(action),
            expression=expression,
            name=name,
            products=products,
            priority=priority,
            reference_tag=reference_tag,
        )

        siemplify.result.add_result_json(rules[0].to_json())
        output_message = f"Successfully created a new firewall rule in {zone_name} zone in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        output_message = (
            f'Error executing action "{CREATE_FIREWALL_RULE_SCRIPT_NAME}". Reason: {e}'
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

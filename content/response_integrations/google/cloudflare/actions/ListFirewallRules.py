from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.CloudflareManager import CloudflareManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_FIREWALL_RULES_SCRIPT_NAME,
    FILTER_KEY_MAPPING,
    FILTER_STRATEGY_MAPPING,
    DEFAULT_LIMIT,
)


TABLE_NAME = "Available Rules"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_FIREWALL_RULES_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
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
        siemplify, param_name="Zone Name", print_value=True, is_mandatory=True
    )
    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", print_value=True
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = f"Successfully found rules for the provided criteria in {INTEGRATION_DISPLAY_NAME}."
    result_value = True

    try:
        if limit <= 0:
            raise Exception(
                f'Invalid value provided for "Max Records to Return": {limit}. '
                f"Positive number should be provided"
            )

        if not FILTER_KEY_MAPPING.get(filter_key) and FILTER_STRATEGY_MAPPING.get(
            filter_logic
        ):
            raise Exception(
                'you need to select a field from the "Filter Key" parameter'
            )

        manager = CloudflareManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            account_name=account_name,
            siemplify_logger=siemplify.LOGGER,
        )

        zone = manager.get_zone(zone_name=zone_name)
        rules = manager.list_firewall_rules(
            zone_id=zone.zone_id,
            filter_key=FILTER_KEY_MAPPING.get(filter_key),
            filter_logic=filter_logic,
            filter_value=filter_value,
            limit=limit,
        )

        if rules:
            siemplify.result.add_data_table(
                title=TABLE_NAME,
                data_table=construct_csv([rule.to_table() for rule in rules]),
            )
            siemplify.result.add_result_json([rule.to_json() for rule in rules])
            if filter_value is None:
                output_message += '\nThe filter was not applied, because parameter "Filter Value" has an empty value.'
        else:
            result_value = False
            output_message = f"No rules were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}"

    except Exception as e:
        output_message = (
            f'Error executing action "{LIST_FIREWALL_RULES_SCRIPT_NAME}". Reason: {e}'
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

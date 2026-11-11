from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    LIST_SITES_SCRIPT_NAME,
    FILTER_KEY_MAPPING,
    FILTER_STRATEGY_MAPPING,
)

TABLE_NAME = "Available Sites"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_SITES_SCRIPT_NAME
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

    # Action parameters
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
        default_value=50,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if not FILTER_KEY_MAPPING.get(filter_key) and FILTER_STRATEGY_MAPPING.get(
            filter_logic
        ):
            raise Exception(
                'you need to select a field from the "Filter Key" parameter'
            )

        if limit <= 0:
            raise Exception(
                f'Invalid value was provided for "Max Records to Return": {limit}. '
                f"Positive number should be provided"
            )

        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        sites = manager.get_sites(filter_key, filter_logic, filter_value, limit)

        if sites:
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([site.to_csv() for site in sites])
            )
            siemplify.result.add_result_json([site.to_json() for site in sites])
            output_message = (
                f"Successfully found sites for the provided criteria in {PRODUCT_NAME}."
            )
        else:
            result = False
            output_message = (
                f"No sites were found for the provided criteria in {PRODUCT_NAME}."
            )

        if (
            FILTER_KEY_MAPPING.get(filter_key)
            and FILTER_STRATEGY_MAPPING.get(filter_logic)
            and not filter_value
        ):
            output_message += '\nThe filter was not applied, because parameter "Filter Value" has an empty value.'

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_SITES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_SITES_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

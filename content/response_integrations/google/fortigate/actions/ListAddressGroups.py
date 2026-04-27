from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.FortigateManager import FortigateManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_ADDRESS_GROUPS_SCRIPT_NAME,
    FILTER_LOGIC_OPERATORS,
    FILTER_KEY_VALUES,
)
from TIPCommon import construct_csv


TABLE_NAME = "Available Address Groups"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ADDRESS_GROUPS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
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
        if not FILTER_KEY_VALUES.get(filter_key) and FILTER_LOGIC_OPERATORS.get(
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

        manager = FortigateManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        address_groups = manager.list_address_groups(
            filter_key, filter_logic, filter_value, limit
        )

        if address_groups:
            siemplify.result.add_data_table(
                TABLE_NAME,
                construct_csv(
                    [address_group.to_table() for address_group in address_groups]
                ),
            )
            siemplify.result.add_result_json(
                [address_group.to_json() for address_group in address_groups]
            )
            output_message = f"Successfully found address groups for the provided criteria in {INTEGRATION_DISPLAY_NAME}"
        else:
            result = False
            output_message = f"No address groups were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}"

        if (
            FILTER_KEY_VALUES.get(filter_key)
            and FILTER_LOGIC_OPERATORS.get(filter_logic)
            and not filter_value
        ):
            output_message += '\nThe filter was not applied, because parameter "Filter Value" has an empty value.'

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_ADDRESS_GROUPS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_ADDRESS_GROUPS_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

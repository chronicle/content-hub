from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.IvantiEndpointManagerManager import IvantiEndpointManagerManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_DELIVERY_METHODS_SCRIPT_NAME,
)


TABLE_NAME = "Available Delivery Methods"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_DELIVERY_METHODS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
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
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    type = extract_action_param(siemplify, param_name="Type", print_value=True)
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Delivery Methods To Return",
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_results = {}

    try:
        if limit is not None and limit < 1:
            raise Exception('"Max Delivery Methods To Return" must be greater than 0.')

        manager = IvantiEndpointManagerManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        delivery_methods = manager.get_delivery_methods(
            type, filter_logic, filter_value, limit
        )

        if delivery_methods:
            json_results["DeliveryMethods"] = [
                delivery_method.to_json() for delivery_method in delivery_methods
            ]
            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table(
                TABLE_NAME,
                construct_csv(
                    [delivery_method.to_table() for delivery_method in delivery_methods]
                ),
            )
            output_message += (
                f"Successfully found delivery methods for the provided criteria in "
                f"{INTEGRATION_DISPLAY_NAME}."
            )
        else:
            output_message = f"No delivery methods were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_DELIVERY_METHODS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_DELIVERY_METHODS_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

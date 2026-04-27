from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.IvantiEndpointManagerManager import IvantiEndpointManagerManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_QUERIES_SCRIPT_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_QUERIES_SCRIPT_NAME
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
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify, param_name="Max Queries To Return", input_type=int, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_results = {}

    try:
        if limit is not None and limit < 1:
            raise Exception('"Max Queries To Return" must be greater than 0.')

        manager = IvantiEndpointManagerManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        queries = manager.get_queries(filter_logic, filter_value, limit)

        if queries:
            json_results["queries"] = [query.to_json() for query in queries]
            siemplify.result.add_result_json(json_results)
            output_message += f"Successfully found queries for the provided criteria in {INTEGRATION_DISPLAY_NAME}."
        else:
            output_message = f"No queries were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_QUERIES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_QUERIES_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

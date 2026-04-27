from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.HumioManager import HumioManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME,
)


TABLE_NAME = "Results"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME
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
    repository_name = extract_action_param(
        siemplify, param_name="Repository Name", is_mandatory=True, print_value=True
    )
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        if limit is not None and limit < 1:
            raise Exception('"Max Results To Return" must be greater than 0.')

        manager = HumioManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        results, constructed_query = manager.get_events_by_custom_query(
            repository_name, query, limit
        )

        if results:
            siemplify.result.add_result_json([result.to_json() for result in results])
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([result.to_table() for result in results])
            )
            output_message += (
                f'Successfully returned results for the query "{constructed_query}" in '
                f"{INTEGRATION_DISPLAY_NAME}."
            )
        else:
            output_message = f'No results were found for the query "{constructed_query}" in {INTEGRATION_DISPLAY_NAME}.'

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{EXECUTE_CUSTOM_SEARCH_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

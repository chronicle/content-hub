from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.AppSheetManager import AppSheetManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    DELETE_RECORD_SCRIPT_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_RECORD_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    app_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="App ID",
        is_mandatory=True,
        print_value=True,
    )
    access_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Token",
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    table_name = extract_action_param(
        siemplify, param_name="Table Name", is_mandatory=True, print_value=True
    )
    json_query = extract_action_param(
        siemplify, param_name="Record JSON Object", is_mandatory=True, print_value=True
    )

    output_message = ""
    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        appsheet_manager = AppSheetManager(
            api_root=api_root,
            app_id=app_id,
            access_token=access_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        record_details = appsheet_manager.delete_record(
            table_name=table_name, query=json_query
        )

        if len(record_details) > 0:
            number_of_rows = record_details[0].get("_RowNumber")
            if number_of_rows is None:
                output_message = (
                    f"Provided record didn\'t exist in table  '{table_name}' in "
                    f"{INTEGRATION_DISPLAY_NAME}"
                )

            else:
                siemplify.result.add_result_json(record_details)
                output_message = (
                    f"Successfully deleted record in table '{table_name}' in "
                    f"{INTEGRATION_DISPLAY_NAME}"
                )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {DELETE_RECORD_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{DELETE_RECORD_SCRIPT_NAME}'. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

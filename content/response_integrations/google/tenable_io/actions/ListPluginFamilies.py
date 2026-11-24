from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tenable_io.core.TenableIOManager import TenableIOManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from tenable_io.core.constants import (
    INTEGRATION_NAME,
    LIST_PLUGIN_FAMILIES_SCRIPT_NAME,
    EQUAL_FILTER,
    CONTAINS_FILTER,
    DEFAULT_PLUGIN_FAMILIES_LIMIT,
)

TABLE_NAME = "Available Plugin Families"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_PLUGIN_FAMILIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        is_mandatory=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Plugin Families To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_PLUGIN_FAMILIES_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if limit < 1:
            raise Exception('"Max Plugin Families To Return" must be greater than 0.')

        manager = TenableIOManager(
            api_root=api_root,
            secret_key=secret_key,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        siemplify.LOGGER.info(
            "Retrieving information about available plugin families..."
        )
        plugin_families = manager.list_plugin_families()
        if filter_value:
            if filter_logic == EQUAL_FILTER:
                plugin_families = [
                    family for family in plugin_families if family.name == filter_value
                ]
            elif filter_logic == CONTAINS_FILTER:
                plugin_families = [
                    family for family in plugin_families if filter_value in family.name
                ]

        plugin_families = plugin_families[:limit] if limit else plugin_families

        if plugin_families:
            siemplify.result.add_data_table(
                TABLE_NAME,
                construct_csv([family.to_csv() for family in plugin_families]),
            )
            siemplify.result.add_result_json(
                [family.to_json() for family in plugin_families]
            )
            output_message = (
                f"Successfully listed available plugin families based on the provided criteria in"
                f" {INTEGRATION_NAME}."
            )
        else:
            result_value = False
            output_message = f"No plugin families were found based on the provided criteria in {INTEGRATION_NAME}."

    except Exception as e:
        output_message = (
            f"Error executing action {LIST_PLUGIN_FAMILIES_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

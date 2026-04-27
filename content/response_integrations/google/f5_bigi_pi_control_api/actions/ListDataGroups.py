from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.F5BIGIPiControlAPIManager import F5BIGIPiControlAPIManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_DATA_GROUPS_SCRIPT_NAME,
    EQUAL_FILTER,
    CONTAINS_FILTER,
    DEFAULT_LIMIT,
)

TABLE_NAME = "Available Data Groups"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_DATA_GROUPS_SCRIPT_NAME
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
        param_name="Max Data Groups To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if limit < 1:
            raise Exception('"Max Data Groups To Return" must be greater than 0.')

        manager = F5BIGIPiControlAPIManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Retrieving information about available data groups...")
        data_groups = manager.list_data_groups(paginate=bool(filter_value))
        if filter_value:
            if filter_logic == EQUAL_FILTER:
                data_groups = [
                    data_group
                    for data_group in data_groups
                    if data_group.name == filter_value
                ]
            elif filter_logic == CONTAINS_FILTER:
                data_groups = [
                    data_group
                    for data_group in data_groups
                    if filter_value in data_group.name
                ]

        data_groups = data_groups[:limit] if limit else data_groups

        if data_groups:
            siemplify.result.add_data_table(
                TABLE_NAME,
                construct_csv([data_group.to_csv() for data_group in data_groups]),
            )
            siemplify.result.add_result_json(
                [data_group.to_json() for data_group in data_groups]
            )
            output_message = (
                f"Successfully found data groups for the provided criteria in"
                f" {INTEGRATION_NAME}."
            )
        else:
            result_value = False
            output_message = f"No data groups were found for the provided criteria in {INTEGRATION_NAME}."

    except Exception as e:
        output_message = (
            f"Error executing action {LIST_DATA_GROUPS_SCRIPT_NAME}. Reason: {e}"
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

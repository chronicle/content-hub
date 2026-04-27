from __future__ import annotations
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    LIST_QUERIES_SCRIPT_NAME,
    LIST_QUERIES_TABLE_NAME,
    FilterStrategy,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_QUERIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ServerAddress",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    group_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="GroupName"
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", default_value=FilterStrategy.Equal.name
    )
    filter_value = extract_action_param(siemplify, param_name="Filter Value")
    limit = extract_action_param(
        siemplify,
        param_name="Max Results To Return",
        print_value=True,
        input_type=int,
        default_value=50,
    )

    result_value = False
    output_message = (
        f"No queries were found by {PRODUCT_NAME} based on the provided criteria."
    )
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = McafeeEpoManager(
            api_root=api_root,
            username=username,
            password=password,
            group_name=group_name,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        queries_list = manager.get_list_queries_by_filter(
            value=filter_value, filter_strategy=filter_logic, limit=limit
        )

        if queries_list:
            siemplify.result.add_result_json(
                [query.to_json() for query in queries_list]
            )
            siemplify.result.add_data_table(
                LIST_QUERIES_TABLE_NAME,
                construct_csv([query.to_csv() for query in queries_list]),
            )
            result_value = True
            output_message = f"Successfully listed available queries {PRODUCT_NAME}"

    except Exception as e:
        output_message = (
            f"Error executing action '{LIST_QUERIES_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

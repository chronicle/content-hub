from __future__ import annotations
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    EXECUTE_QUERY_BY_ID_SCRIPT_NAME,
    QUERY_DATA_TABLE_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_QUERY_BY_ID_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ServerAddress",
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
    group_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="GroupName",
        print_value=True,
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

    query_id = extract_action_param(
        siemplify, param_name="Query ID", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify, param_name="Max Results To Return", input_type=int, print_value=True
    )
    limit = limit and max(0, limit) or None

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = f"No results were found for the query {query_id} in {PRODUCT_NAME}"

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

        query_results = manager.run_query_by_id(query_id=query_id, result_limit=limit)

        if query_results:
            siemplify.result.add_result_json(
                [query_result.to_underscored_json() for query_result in query_results]
            )
            siemplify.result.add_data_table(
                QUERY_DATA_TABLE_NAME,
                construct_csv(
                    [
                        query_result.to_underscored_csv()
                        for query_result in query_results
                    ]
                ),
            )
            output_message = f"Successfully returned results for the query {query_id} in {PRODUCT_NAME}"
            result_value = True

    except Exception as e:
        output_message = (
            f"Error executing action '{EXECUTE_QUERY_BY_ID_SCRIPT_NAME}'. Reason: {e}"
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

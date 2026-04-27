from __future__ import annotations
from ..core.McAfeeManager import McafeeEpoManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    EXECUTE_CUSTOM_QUERY_SCRIPT_NAME,
    CUSTOM_QUERY_TABLE_NAME,
)
from ..core.utils import string_to_multi_value

DEFAULT_LIMIT = 50


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_CUSTOM_QUERY_SCRIPT_NAME
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

    table_name = extract_action_param(
        siemplify, param_name="Table Name", is_mandatory=True
    )
    fields_to_return = string_to_multi_value(
        string_value=extract_action_param(siemplify, param_name="Fields To Return")
    )
    fields_to_return = [field.replace("_", ".") for field in fields_to_return or []]
    where = extract_action_param(siemplify, param_name="Where Clause")

    sort_field = extract_action_param(siemplify, param_name="Sort Field")
    sort_field = sort_field.replace("_", ".") if sort_field else sort_field
    sort_order = extract_action_param(siemplify, param_name="Sort Order")

    results_limit = extract_action_param(
        siemplify, param_name="Max Results To Return", input_type=int
    )
    results_limit = results_limit and max(0, results_limit) or DEFAULT_LIMIT

    result_value = True
    output_message = f"No results were found for the provided query in {PRODUCT_NAME}"
    status = EXECUTION_STATE_COMPLETED
    csv_result, json_result = [], []

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

        results = manager.execute_custom_query(
            table_name=table_name,
            fields_to_return=fields_to_return,
            where_condition=where,
            sort_field=sort_field,
            sort_order=sort_order,
            limit=results_limit,
        )

        if results:
            output_message = f"Successfully returned results for the provided query in {PRODUCT_NAME}"
            for result in results:
                json_result.append(result.to_json())
                csv_result.append(result.to_csv())

            siemplify.result.add_result_json(json_result)
            siemplify.result.add_data_table(
                CUSTOM_QUERY_TABLE_NAME, construct_csv(csv_result)
            )

    except Exception as e:
        output_message = (
            f"Error executing action '{EXECUTE_CUSTOM_QUERY_SCRIPT_NAME}'. Reason: {e}"
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

from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.NozomiNetworksManager import NozomiNetworksManager
from ..core.NozomiNetworksConstants import PROVIDER_NAME, RUN_QUERY_SCRIPT_NAME

TABLE_TITLE = "Query Results"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = RUN_QUERY_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configurations
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API URL",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
    )

    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
        print_value=False,
    )

    # Parameters
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    record_limit = extract_action_param(
        siemplify, param_name="Record Limit", input_type=int, print_value=True
    )

    record_limit = None if record_limit < 0 else record_limit

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = NozomiNetworksManager(
            api_root=api_root,
            username=username,
            password=password,
            ca_certificate_file=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        query_results = manager.run_query(query=query, record_limit=record_limit)

        if query_results:
            output_message = "Query executed successfully."
            siemplify.result.add_result_json([item.to_json() for item in query_results])
            result_value = True
        else:
            output_message = (
                "Query executed successfully, but did not return any results."
            )

    except Exception as e:
        output_message = f'Failed to execute "Run a Query" action! Error is: {e}'
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

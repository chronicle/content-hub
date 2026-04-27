from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.ArcsightManager import ArcsightManager
from ..core.UtilsManager import get_suitable_resources_ids
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.exceptions import ArcsightInvalidParamError
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_RESOURCES_SCRIPT_NAME,
    UNSUPPORTED_REPORT_UUID_PREFIXES,
)

QUERIES_TABLE_NAME = "Available Queries"
ACTIVE_LIST_TABLE_NAME = "Available Active List"
CASES_TABLE_NAME = "Available Cases"
REPORTS_TABLE_NAME = "Available Reports"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_RESOURCES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
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
    ca_certificate_file = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="CA Certificate File"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    return_active_list = extract_action_param(
        siemplify, param_name="Return Active Lists", print_value=True, input_type=bool
    )
    return_queries = extract_action_param(
        siemplify, param_name="Return Queries", print_value=True, input_type=bool
    )
    return_cases = extract_action_param(
        siemplify, param_name="Return Cases", print_value=True, input_type=bool
    )
    return_reports = extract_action_param(
        siemplify, param_name="Return Reports", print_value=True, input_type=bool
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Resources To Return",
        print_value=True,
        input_type=int,
    )
    limit = None if limit and limit <= 0 else limit

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = f"Successfully retrieved available resources in {INTEGRATION_NAME}"
    result = {}

    try:
        if (
            not return_active_list
            and not return_queries
            and not return_cases
            and not return_reports
        ):
            raise ArcsightInvalidParamError(
                "at least one of the 'Return ...' parameters should be enabled."
            )

        arcsight_manager = ArcsightManager(
            server_ip=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
            logger=siemplify.LOGGER,
        )
        arcsight_manager.login()

        if return_queries:
            queries_ids = arcsight_manager.get_query_resources_ids(limit=limit)
            if queries_ids:
                queries = arcsight_manager.get_query_resources_by_ids(queries_ids)
                result["queries"] = [query.to_json() for query in queries]
                siemplify.result.add_data_table(
                    QUERIES_TABLE_NAME,
                    construct_csv([query.to_table() for query in queries]),
                )

        if return_active_list:
            active_list_ids = arcsight_manager.get_active_lists_ids(limit=limit)
            if active_list_ids:
                active_lists = arcsight_manager.get_active_lists_resources_by_ids(
                    active_list_ids
                )
                result["active_lists"] = [
                    active_list.to_json() for active_list in active_lists
                ]
                siemplify.result.add_data_table(
                    ACTIVE_LIST_TABLE_NAME,
                    construct_csv(
                        [active_list.to_table() for active_list in active_lists]
                    ),
                )

        if return_cases:
            cases_ids = arcsight_manager.get_case_resources_ids(limit=limit)
            if cases_ids:
                cases = arcsight_manager.get_case_resources_by_ids(cases_ids)
                result["cases"] = [case.to_json() for case in cases]
                siemplify.result.add_data_table(
                    CASES_TABLE_NAME, construct_csv([case.to_table() for case in cases])
                )

        if return_reports:
            reports_ids = arcsight_manager.get_report_resources_ids()
            suitable_reports_ids = get_suitable_resources_ids(
                reports_ids, UNSUPPORTED_REPORT_UUID_PREFIXES
            )[:limit]
            if suitable_reports_ids:
                reports = arcsight_manager.get_report_resources_by_ids(
                    suitable_reports_ids
                )
                result["reports"] = [report.to_json() for report in reports]
                siemplify.result.add_data_table(
                    REPORTS_TABLE_NAME,
                    construct_csv([report.to_table() for report in reports]),
                )

        if (
            not result.get("queries")
            and not result.get("active_lists")
            and not result.get("cases")
            and not result.get("reports")
        ):
            output_message = f"No resources were found in {INTEGRATION_NAME}"
            result_value = False

        siemplify.result.add_result_json(result)
        arcsight_manager.logout()

    except Exception as e:
        output_message = (
            f"Error executing action '{LIST_RESOURCES_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

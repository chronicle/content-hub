from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.NozomiNetworksManager import NozomiNetworksManager
from ..core.NozomiNetworksConstants import (
    PROVIDER_NAME,
    LIST_VULNERABILITIES_SCRIPT_NAME,
    DEFAULT_RECORD_LIMIT,
)

TABLE_TITLE = "Vulnerabilities Found"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_VULNERABILITIES_SCRIPT_NAME

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
    ip_adresses = extract_action_param(
        siemplify,
        param_name="IP Address",
        default_value="",
        is_mandatory=False,
        print_value=True,
    )
    cve_score = extract_action_param(
        siemplify,
        param_name="CVE Score",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )
    vulnerability_name_contains = extract_action_param(
        siemplify,
        param_name="Vulnerability Name Contains",
        is_mandatory=False,
        print_value=True,
    )
    cve_ids = extract_action_param(
        siemplify,
        param_name="CVE ID",
        default_value="",
        is_mandatory=False,
        print_value=True,
    )
    record_limit = extract_action_param(
        siemplify,
        param_name="Record Limit",
        default_value=DEFAULT_RECORD_LIMIT,
        input_type=int,
        print_value=True,
    )
    include_resolved = extract_action_param(
        siemplify,
        param_name="Include vulnerabilities that marked as resolved?",
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    if cve_score and cve_score > 10:
        cve_score = 10
        siemplify.LOGGER.info(
            "CVE Score should not be higher than 10. Setting value to 10"
        )
    elif cve_score and cve_score < 0:
        cve_score = 0
        siemplify.LOGGER.info(
            "CVE Score should not be lower than 0. Setting value to 0"
        )

    try:
        manager = NozomiNetworksManager(
            api_root=api_root,
            username=username,
            password=password,
            ca_certificate_file=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        vulnerabilities = manager.get_vulnerabilities(
            ip_addresses=[ip.strip() for ip in ip_adresses.split(",") if ip.strip()],
            cve_score=cve_score,
            name_contains=vulnerability_name_contains,
            cve_ids=[cve.strip() for cve in cve_ids.split(",") if cve.strip()],
            record_limit=record_limit,
            include_resolved=include_resolved,
        )

        if vulnerabilities:
            output_message = "Search executed successfully."
            siemplify.result.add_result_json(
                [item.to_json() for item in vulnerabilities]
            )
            siemplify.result.add_data_table(
                TABLE_TITLE, construct_csv([item.to_csv() for item in vulnerabilities])
            )
            result_value = True
        else:
            output_message = (
                "Search executed successfully, but did not return any results."
            )

    except Exception as e:
        output_message = (
            f'Failed to execute "List Vulnerabilities" action! Error is: {e}'
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

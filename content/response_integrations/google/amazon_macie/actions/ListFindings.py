from __future__ import annotations
from datetime import timedelta

import pytz
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core import consts
from ..core import utils
from ..core.AmazonMacieManager import AmazonMacieManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, utc_now, convert_datetime_to_unix_time
from ..core.consts import INTEGRATION_NAME
from ..core.exceptions import AmazonMacieValidationException

SCRIPT_NAME = "List Findings"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    finding_types = extract_action_param(
        siemplify, param_name="Finding Type", is_mandatory=False, print_value=True
    )
    severities = extract_action_param(
        siemplify, param_name="Severity", is_mandatory=False, print_value=True
    )
    include_archived = extract_action_param(
        siemplify,
        param_name="Include Archived Findings?",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    time_frame = extract_action_param(
        siemplify,
        param_name="Time Frame",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=4,
    )
    max_results_to_return = extract_action_param(
        siemplify,
        param_name="Record Limit",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )
    sort_by = extract_action_param(
        siemplify, param_name="Sort By", is_mandatory=False, print_value=True
    )
    order_by = extract_action_param(
        siemplify,
        param_name="Sort Order",
        is_mandatory=False,
        print_value=True,
        default_value=consts.ASC,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    json_results = []

    try:
        # Split the CSVs
        finding_types = (
            utils.load_csv_to_list(finding_types, "Finding Type")
            if finding_types
            else []
        )
        severities = (
            utils.load_csv_to_list(severities, "Severity") if severities else []
        )

        for severity in severities:
            if severity.lower() not in consts.VALID_SEVERITIES:
                raise AmazonMacieValidationException(
                    f"Severity {severity} is invalid. Valid values are: Low, Medium, High."
                )

        # Adjust severities case
        severities = [
            consts.VALID_SEVERITIES.get(severity.lower()) for severity in severities
        ]

        time_filter = (
            convert_datetime_to_unix_time(
                utc_now().replace(tzinfo=pytz.utc) - timedelta(hours=int(time_frame))
            )
            if time_frame
            else None
        )

        siemplify.LOGGER.info("Connecting to Amazon Macie Service")
        manager = AmazonMacieManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to Amazon Macie service")

        findings_ids = manager.get_findings_ids(
            finding_types=finding_types,
            severities=severities,
            time_filter=time_filter,
            include_archived=include_archived,
            sort_by=sort_by,
            order_by=order_by,
            max_results=max_results_to_return,
        )

        siemplify.LOGGER.info(f"Found {len(findings_ids)} findings IDs.")

        if findings_ids:
            siemplify.LOGGER.info(f"Fetching findings details.")
            findings = manager.get_findings_by_ids(findings_ids=findings_ids)

            if findings:
                siemplify.LOGGER.info(f"Found {len(findings)} findings details.")
                siemplify.result.add_data_table(
                    "Amazon Macie Findings",
                    construct_csv([finding.as_csv() for finding in findings]),
                )
                output_message += "Amazon Macie findings found"
                result_value = "true"
            else:
                siemplify.LOGGER.info(f"No findings were found.")
                output_message += "No findings were returned."

            json_results = [finding.raw_data for finding in findings]

        else:
            siemplify.LOGGER.info(f"No findings were found.")
            output_message += "No findings were returned."

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Failed to connect to the Amazon Macie service! Error is {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the Amazon Macie service! Error is {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

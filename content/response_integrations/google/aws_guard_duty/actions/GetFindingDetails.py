from __future__ import annotations
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME
from ..core import utils

SCRIPT_NAME = "Get Finding Details"


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

    detector_id = extract_action_param(
        siemplify, param_name="Detector ID", is_mandatory=True, print_value=True
    )
    findings_ids = extract_action_param(
        siemplify, param_name="Finding IDs", is_mandatory=True, print_value=True
    )
    aws_region = extract_action_param(
        siemplify,
        param_name="AWS Region",
        is_mandatory=False,
        print_value=True,
        default_value=aws_default_region,
    )

    # Split the findings IDs
    findings_ids = utils.load_csv_to_list(findings_ids, "Finding IDs")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    json_results = {}

    try:
        siemplify.LOGGER.info("Connecting to AWS GuardDuty Service")
        manager = AWSGuardDutyManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_region,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS GuardDuty service")

        siemplify.LOGGER.info(f"Fetching findings details for detector {detector_id}")
        findings = manager.get_findings_by_ids(
            detector_id=detector_id, findings_ids=findings_ids
        )

        if findings:
            siemplify.LOGGER.info(f"Found {len(findings)} findings details.")
            siemplify.result.add_data_table(
                "Findings", construct_csv([finding.as_csv() for finding in findings])
            )

            found_findings_ids = [finding.id for finding in findings]
            not_found_ids = []

            for findings_id in findings_ids:
                if findings_id not in found_findings_ids:
                    not_found_ids.append(findings_id)

            if found_findings_ids:
                output_message += "Successfully retrieved information for the following findings:\n{}\n\n".format(
                    "\n".join(found_findings_ids)
                )

            if not_found_ids:
                output_message += "Failed to retrieve information for the following findings:\n{}".format(
                    "\n".join(not_found_ids)
                )

        else:
            siemplify.LOGGER.info(f"No findings details were found.")
            output_message += (
                "Failed to retrieve information for the following findings:\n{}".format(
                    "\n".join(findings_ids)
                )
            )
            result_value = "false"

        json_results["Findings"] = [finding.raw_data for finding in findings]

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

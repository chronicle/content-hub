from __future__ import annotations
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME
from ..core import utils

SCRIPT_NAME = "Unarchive Findings"


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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    unarchived_findings = []
    output_message = ""
    result_value = "false"

    try:
        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
        manager = AWSGuardDutyManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service"
        )

        # Split the findings IDs
        findings_ids = utils.load_csv_to_list(findings_ids, "Finding IDs")

        siemplify.LOGGER.info(f"Un-archiving findings of detector {detector_id}")

        fetched_findings = manager.get_findings_by_ids(
            detector_id=detector_id, findings_ids=findings_ids
        )
        fetched_findings_ids = [finding.id for finding in fetched_findings]
        not_unarchived_findings = [
            id for id in findings_ids if id not in fetched_findings_ids
        ]

        for finding in fetched_findings_ids:
            try:
                manager.unarchive_findings(
                    detector_id=detector_id, finding_ids=[finding]
                )
                siemplify.LOGGER.info(
                    f"Successfully un-archiving finding with id {finding} of detector {detector_id}"
                )
                unarchived_findings.append(finding)

            except Exception as error:
                siemplify.LOGGER.info(
                    f"Action wasn’t able to un-archive Finding: {finding} Error {error}"
                )
                siemplify.LOGGER.exception(
                    f"Action wasn’t able to un-archive Finding {finding} Error {error}"
                )

        if unarchived_findings:
            output_message += (
                "The following findings were successfully un-archived: "
                + ", ".join(unarchived_findings)
                + "\n"
            )
            result_value = "true"

        if not_unarchived_findings:
            output_message += (
                "Could not un-archive the following findings: "
                + ", ".join(not_unarchived_findings)
            )

        status = EXECUTION_STATE_COMPLETED

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
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

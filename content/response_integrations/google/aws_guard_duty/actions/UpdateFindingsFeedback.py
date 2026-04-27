from __future__ import annotations
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME, USEFUL, NOT_USEFUL, INTEGRATION_DISPLAY_NAME
from ..core import utils


SCRIPT_NAME = "Update Findings Feedback"


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

    is_useful = extract_action_param(
        siemplify,
        param_name="Useful?",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    finding_ids = extract_action_param(
        siemplify, param_name="Findings IDs", is_mandatory=True, print_value=True
    )

    comment = extract_action_param(
        siemplify, param_name="Comment", is_mandatory=False, print_value=True
    )

    aws_region = extract_action_param(
        siemplify,
        param_name="AWS Region",
        is_mandatory=False,
        print_value=True,
        default_value=aws_default_region,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    not_updated_finding = []
    output_message = ""
    updated_findings = ""
    failed_to_update_findings = ""

    try:
        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
        manager = AWSGuardDutyManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_region,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service"
        )

        # Split the findings IDs
        finding_ids = utils.load_csv_to_list(finding_ids, "Findings IDs")
        useful = USEFUL if is_useful else NOT_USEFUL

        # Get finding by id's to see if exist
        findings_found = manager.get_findings_by_ids(
            detector_id=detector_id, findings_ids=finding_ids
        )

        fetched_findings = [find.id for find in findings_found]
        for id in finding_ids:
            if id not in fetched_findings:
                not_updated_finding.append(id)
                failed_to_update_findings += f"{id} "
            else:
                updated_findings += f"{id} "

        siemplify.LOGGER.info(f"Update Findings Feedback for {fetched_findings}")
        manager.update_findings_feedback(
            detector_id=detector_id,
            useful=useful,
            finding_ids=fetched_findings,
            comment=comment,
        )
        siemplify.LOGGER.info(
            f"Successfully Updated Findings Feedback for {fetched_findings}"
        )

        status = EXECUTION_STATE_COMPLETED

        output_message += (
            f"Findings feedback was updated for finding: {updated_findings}"
            if fetched_findings
            else ""
        )

        output_message += (
            f"Unable to update feedback findings: {failed_to_update_findings}"
            if not_updated_finding
            else ""
        )

        result_value = "true" if fetched_findings else "false"

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

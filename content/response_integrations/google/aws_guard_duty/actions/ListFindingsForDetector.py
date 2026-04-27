from __future__ import annotations
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME, DEFAULT_MAX_RESULTS, ASC

SCRIPT_NAME = "List Findings for a Detector"


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

    max_results_to_return = extract_action_param(
        siemplify,
        param_name="Max Findings To Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )

    sort_by = extract_action_param(
        siemplify, param_name="Sort By", is_mandatory=False, print_value=True
    )

    order_by = extract_action_param(
        siemplify,
        param_name="Order By",
        is_mandatory=False,
        print_value=True,
        default_value=ASC,
    )
    aws_region = extract_action_param(
        siemplify,
        param_name="AWS Region",
        is_mandatory=False,
        print_value=True,
        default_value=aws_default_region,
    )

    if max_results_to_return and max_results_to_return < 0:
        max_results_to_return = DEFAULT_MAX_RESULTS
        siemplify.LOGGER.info(
            f"Max Trusted IP Lists To Return parameter must be non-positive. Using default value of {DEFAULT_MAX_RESULTS}"
        )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
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

        siemplify.LOGGER.info(f"Fetching findings ids for detector {detector_id}")
        findings_ids = manager.get_findings_ids_for_detector(
            detector_id=detector_id,
            sort_by=sort_by,
            order_by=order_by,
            max_results=max_results_to_return,
        )
        siemplify.LOGGER.info(f"Successfully found {len(findings_ids)} findings ids")
        output_message = (
            f"Successfully retrieved available findings IDs for detector {detector_id}."
        )

        json_results["FindingIds"] = findings_ids

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

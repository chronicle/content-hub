from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.AWSIAMAnalyzerManager import AWSIAMAnalyzerManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME
from ..core.exceptions import AWSIAMNotFoundException, AWSIAMAnalyzerNotFoundException

SCRIPT_NAME = "Archive Finding"


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
    analyzer_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Analyzer Name",
        is_mandatory=True,
    )

    finding_id = extract_action_param(
        siemplify, param_name="Finding ID", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        try:
            siemplify.LOGGER.info(f"Getting analyzer from {INTEGRATION_NAME} Service")
            manager = AWSIAMAnalyzerManager(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_default_region=aws_default_region,
                analyzer_name=analyzer_name,
            )
            analyzer = manager.get_analyzer()
            siemplify.LOGGER.info(
                f"Successfully got analyzer from {INTEGRATION_NAME} Service"
            )
        except AWSIAMNotFoundException as e:
            raise AWSIAMAnalyzerNotFoundException(e)

        siemplify.LOGGER.info(f"Archiving finding {finding_id}")
        manager.archive_finding(ids=[finding_id], analyzer_arn=analyzer.arn)
        siemplify.LOGGER.info(f"Successfully archived finding {finding_id}")
        output_message = (
            f"Successfully archived finding with ID {finding_id} in {INTEGRATION_NAME}"
        )
        result_value = "true"

    except AWSIAMAnalyzerNotFoundException as error:  # Analyzer not found exception
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {analyzer_name} analyzer "
            "was not found"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message += (
            f"Error executing action '{SCRIPT_NAME}'. Reason: {analyzer_name} "
            "analyzer was not found"
        )

    except Exception as error:  # action failed, stops playbook
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

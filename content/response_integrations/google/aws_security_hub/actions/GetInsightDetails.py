from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.AWSSecurityHubManager import AWSSecurityHubManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME

SCRIPT_NAME = "GetInsightDetails"
DEFAULT_MAX_RESULTS = 50


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

    insight_arn = extract_action_param(
        siemplify, param_name="Insight ARN", is_mandatory=True, print_value=True
    )

    max_results_to_return = extract_action_param(
        siemplify,
        param_name="Max Results to Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=DEFAULT_MAX_RESULTS,
    )

    if max_results_to_return < 0:
        max_results_to_return = DEFAULT_MAX_RESULTS
        siemplify.LOGGER.info(
            "Max Results to Return parameter is negative. Using default Max Objects "
            f"to Return parameter of {DEFAULT_MAX_RESULTS}"
        )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    json_results = {}

    try:
        siemplify.LOGGER.info("Connecting to AWS Security Hub Service")
        hub_client = AWSSecurityHubManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        hub_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS Security Hub service")

        siemplify.LOGGER.info(f"Fetching list of insight results for arn {insight_arn}")
        insight_results = hub_client.get_insight_results(
            insight_arn=insight_arn, max_results=max_results_to_return
        )
        siemplify.LOGGER.info(
            f"Successfully returned details about Insight with ARN {insight_arn} in "
            "AWS Security Hub"
        )
        output_message += (
            f"Successfully returned details about Insight with ARN {insight_arn} in "
            "AWS Security Hub"
        )

        json_results["InsightResults"] = insight_results.to_dict()
        siemplify.result.add_data_table(
            title="Results",
            data_table=construct_csv(
                [result.as_csv() for result in insight_results.result_values]
            ),
        )

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action 'Get Insight Details'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f"Error executing action 'Get Insight Details'. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

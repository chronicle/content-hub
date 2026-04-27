from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.AWSSecurityHubManager import AWSSecurityHubManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.UtilsManager import validate_filter_json_object
from ..core.consts import INTEGRATION_NAME, MAPPED_GROUP_BY_ATTRIBUTE
from ..core.exceptions import (
    AWSSecurityHubStatusCodeException,
    AWSSecurityHubValidationException,
)

SCRIPT_NAME = "UpdateInsight"


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

    insight_name = extract_action_param(
        siemplify, param_name="Insight Name", is_mandatory=False, print_value=True
    )

    group_by_attribute = extract_action_param(
        siemplify,
        param_name="Group By Attribute",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )

    filter_json = extract_action_param(
        siemplify,
        param_name="Filter JSON Object",
        is_mandatory=False,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        if filter_json:  # if parameter exists
            siemplify.LOGGER.info("Parsing Filter JSON Object.")
            filter_json = validate_filter_json_object(filter_json)
            siemplify.LOGGER.info("Successfully parsed Filter JSON Object.")

        if (
            group_by_attribute and group_by_attribute != "Select One"
        ):  # if group by attribute exists
            siemplify.LOGGER.info("Group By Attribute parameter is specified by user.")
            group_by_attribute = MAPPED_GROUP_BY_ATTRIBUTE.get(group_by_attribute)
            if not group_by_attribute:  # validate group by attribute
                raise AWSSecurityHubValidationException(
                    "Failed to validate Group By Attribute."
                )
            siemplify.LOGGER.info("Group By Attribute parameter validated.")
        else:
            siemplify.LOGGER.info(
                "Group By Attribute parameter is not specified, ignoring parameter."
            )
            group_by_attribute = None

        siemplify.LOGGER.info("Connecting to AWS Security Hub Service")
        hub_client = AWSSecurityHubManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        hub_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS Security Hub service")

        siemplify.LOGGER.info(f"Updating insight {insight_name}")
        hub_client.update_insight(
            insight_arn=insight_arn,
            insight_name=insight_name,
            filter_json=filter_json,
            group_by_attribute=group_by_attribute,
        )

        siemplify.LOGGER.info(f"Successfully updated {insight_arn} in AWS Security Hub")
        output_message += f"Successfully updated {insight_arn} in AWS Security Hub"

    except (
        AWSSecurityHubStatusCodeException,
        AWSSecurityHubValidationException,
    ) as error:
        result_value = "false"
        siemplify.LOGGER.error(
            f"Action wasn’t able to update {insight_arn} insight. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        output_message += (
            f"Action wasn’t able to update {insight_arn} insight. Reason: {error}"
        )

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action 'Update Insight'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action 'Update Insight'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

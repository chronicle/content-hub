from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.AWSWAFManager import AWSWAFManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    DEFAULT_DDL_SCOPE,
    MAX_RULE_GROUPS,
    DEFAULT_RULE_GROUPS,
    MIN_RULE_GROUPS,
    CLOUDFRONT_SCOPE,
    UNMAPPED_SCOPE,
    REGIONAL_SCOPE,
)
from ..core.utils import get_param_scopes

SCRIPT_NAME = "List Rule Groups"


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

    scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )

    max_rule_groups_to_return = extract_action_param(
        siemplify,
        param_name="Max Rule Groups To Return",
        input_type=int,
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_RULE_GROUPS,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    if max_rule_groups_to_return < MIN_RULE_GROUPS:
        siemplify.LOGGER.info(
            f"'Max Rule Groups To Return' Should be at least {MIN_RULE_GROUPS} Default value:"
            f" {DEFAULT_RULE_GROUPS} will be selected"
        )
        max_rule_groups_to_return = DEFAULT_RULE_GROUPS

    elif max_rule_groups_to_return > MAX_RULE_GROUPS:
        siemplify.LOGGER.info(
            f"'Max Rule Groups To Return' Should be at most {MAX_RULE_GROUPS}."
            f" The parameter will be set to: {MAX_RULE_GROUPS}"
        )
        max_rule_groups_to_return = MAX_RULE_GROUPS

    rule_groups = {REGIONAL_SCOPE: [], CLOUDFRONT_SCOPE: []}

    result_value = False
    output_message = ""
    json_results = {}

    try:
        scopes = get_param_scopes(scope)
        siemplify.LOGGER.info("Connecting to AWS WAF Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS WAF service")

        siemplify.LOGGER.info(f"Fetching Rule Groups from {INTEGRATION_NAME}")
        for sc in scopes:  # get all existing Rule Groups in specified scopes in AWS WAF
            rule_groups[sc].extend(
                waf_client.list_rule_groups(
                    scope=sc, max_results_to_return=max_rule_groups_to_return
                )
            )
        siemplify.LOGGER.info(
            f"Successfully fetched Rule Groups from {INTEGRATION_NAME}"
        )

        siemplify.LOGGER.info(f"Handle CloudFront scope Rule Groups if exists")
        #  Handle cloudfront
        rule_groups_cloudfront = rule_groups[CLOUDFRONT_SCOPE]

        if rule_groups_cloudfront:
            json_results[UNMAPPED_SCOPE[CLOUDFRONT_SCOPE]] = [
                group_rule.as_json() for group_rule in rule_groups_cloudfront
            ]
            csv_cloudfront = [
                group_rule.as_csv() for group_rule in rule_groups_cloudfront
            ]
            siemplify.result.add_data_table(
                "CloudFront Rule Groups", construct_csv(csv_cloudfront)
            )
            result_value = True
            output_message += (
                "Successfully listed available Rule Groups in Cloudfront scope.\n"
            )

        elif CLOUDFRONT_SCOPE in scopes:
            siemplify.LOGGER.info(scopes)
            output_message += (
                "No available Rule Groups were found in Cloudfront scope.\n"
            )

        siemplify.LOGGER.info(
            f"Successfully handled CloudFront scope Rule Groups if exists"
        )

        siemplify.LOGGER.info(f"Handle Regional scope Rule Groups if exists")
        #  Handle regional
        rule_groups_regional = rule_groups[REGIONAL_SCOPE]

        if rule_groups_regional:
            json_results[UNMAPPED_SCOPE[REGIONAL_SCOPE]] = [
                rule_group.as_json() for rule_group in rule_groups_regional
            ]
            csv_regional = [rule_group.as_csv() for rule_group in rule_groups_regional]
            siemplify.result.add_data_table(
                "Regional Rule Groups", construct_csv(csv_regional)
            )
            result_value = True
            output_message += (
                "Successfully listed available Rule Groups in Regional scope.\n"
            )

        elif REGIONAL_SCOPE in scopes:
            output_message += "No available Rule Groups were found in Regional scope.\n"

        siemplify.LOGGER.info(
            f"Successfully handled Regional scope Rule Groups if exists"
        )

        if rule_groups_cloudfront and rule_groups_regional:
            output_message = "Successfully listed available Rule Groups in Regional and CloudFront scopes.\n"

        if not rule_groups_cloudfront and not rule_groups_regional and len(scopes) == 2:
            output_message = (
                "No available Rule Groups were found in Regional and CloudFront scopes."
            )

        if json_results:
            siemplify.result.add_result_json(json_results)

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action “List Rule Groups”. Reason: {error}\n"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

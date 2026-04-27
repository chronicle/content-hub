from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param
from ..core import consts
from ..core.AWSWAFManager import AWSWAFManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME, DEFAULT_DDL_SCOPE, DEFAULT_RULE_GROUP_CAPACITY
from ..core.datamodels import RuleGroup
from ..core.exceptions import AWSWAFDuplicateItemException
from ..core.utils import load_kv_csv_to_dict, get_param_scopes

SCRIPT_NAME = "CreateRuleGroup"


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

    rule_group_name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )

    param_scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )

    capacity = extract_action_param(
        siemplify,
        param_name="Capacity",
        is_mandatory=True,
        print_value=True,
        input_type=int,
        default_value=DEFAULT_RULE_GROUP_CAPACITY,
    )

    sampled_requests_enabled = extract_action_param(
        siemplify,
        param_name="Enable Sampled Requests",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
        default_value=True,
    )

    cloudwatch_metrics_enabled = extract_action_param(
        siemplify,
        param_name="Enable CloudWatch Metrics",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
        default_value=True,
    )
    cloudwatch_metric_name = extract_action_param(
        siemplify,
        param_name="CloudWatch Metric Name",
        is_mandatory=True,
        print_value=True,
    )

    description = extract_action_param(
        siemplify,
        param_name="Description",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )
    tags = extract_action_param(
        siemplify,
        param_name="Tags",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""

    status = EXECUTION_STATE_COMPLETED

    successful_rule_groups = (
        []
    )  # Rule Groups that successfully created in AWS WAF. Values are Rule Group data models
    duplicate_rule_groups = (
        []
    )  # Rule Groups that already exists in AWS WAF. Values are Rule Group data models
    failed_rule_groups = (
        []
    )  # Rule groups that failed to create. Values are Rule Group data models

    json_results = {"Regional": [], "CloudFront": []}

    try:
        tags = load_kv_csv_to_dict(kv_csv=tags, param_name="Tags") if tags else None
        scopes = get_param_scopes(param_scope)

        siemplify.LOGGER.info("Connecting to AWS WAF Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS WAF service")

        for scope in scopes:
            try:
                siemplify.LOGGER.info(
                    f"Creating {scope} rule group {rule_group_name} in AWS WAF"
                )
                created_rule_group = waf_client.create_rule_group(
                    name=rule_group_name,
                    scope=scope,
                    capacity=capacity,
                    sampled_requests_enabled=sampled_requests_enabled,
                    cloudwatch_metrics_enabled=cloudwatch_metrics_enabled,
                    cloudwatch_metric_name=cloudwatch_metric_name,
                    tags=tags,
                    description=description,
                )
                siemplify.LOGGER.info(
                    f"Successfully created {scope} rule group {created_rule_group.name} in AWS WAF"
                )
                json_results[consts.UNMAPPED_SCOPE.get(scope)].append(
                    created_rule_group.name
                )
                successful_rule_groups.append(created_rule_group)

            except (
                AWSWAFDuplicateItemException
            ) as error:  # Rule Group already exists in AWS WAF
                duplicate_rule_groups.append(
                    RuleGroup(name=rule_group_name, scope=scope)
                )
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

            except Exception as error:  # failed to create Rule Group in AWS WAF
                failed_rule_groups.append(
                    RuleGroup(name=rule_group_name, scope=scope)
                )  # failed Rule groups
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

        if duplicate_rule_groups:
            for rule_group in duplicate_rule_groups:
                output_message += f"\n The Rule Group {rule_group.name} already exists in {rule_group.unmapped_scope} scope. \n"
            result_value = "true"

        if (
            successful_rule_groups
        ):  # at least one of the rule groupes created in AWS WAF
            for rule_group in successful_rule_groups:
                output_message += f"\n Successfully created Rule Group {rule_group.name} in {rule_group.unmapped_scope} scope. \n"
            result_value = "true"

        if failed_rule_groups:  # some of the rule groups created, some don't
            for rule_group in failed_rule_groups:
                output_message += f"\n Action was not able to create Rule Group {rule_group.name} in {rule_group.unmapped_scope} scope. \n"

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Create Rule Group'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action 'Create Rule Group'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

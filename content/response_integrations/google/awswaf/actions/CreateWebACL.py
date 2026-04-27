from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param
from ..core import consts
from ..core.AWSWAFManager import AWSWAFManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    DEFAULT_DDL_SCOPE,
    DEFAULT_RULE_SOURCE_TYPE,
    DEFAULT_WEB_ACL_DEFAULT_ACTION,
    DEFAULT_IP_SET_ACTION,
)
from ..core.datamodels import WebACL
from ..core.exceptions import (
    AWSWAFValidationException,
    AWSWAFDuplicateItemException,
    AWSWAFNotFoundException,
)
from ..core.utils import load_kv_csv_to_dict, get_param_scopes

SCRIPT_NAME = "CreateWebACL"


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

    web_acl_name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )

    rule_source_type = extract_action_param(
        siemplify,
        param_name="Rule Source Type",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_RULE_SOURCE_TYPE,
    )

    rule_source_name = extract_action_param(
        siemplify, param_name="Rule Source Name", is_mandatory=True, print_value=True
    )

    param_scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
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

    default_action = extract_action_param(
        siemplify,
        param_name="Default Action",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_WEB_ACL_DEFAULT_ACTION,
    )

    ip_set_action = extract_action_param(
        siemplify,
        param_name="IP Set Action",
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_IP_SET_ACTION,
    )

    rule_priority = extract_action_param(
        siemplify,
        param_name="Rule Priority",
        is_mandatory=True,
        print_value=True,
        input_type=int,
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

    successful_web_acl_groups = (
        []
    )  # Web ACL that successfully created in AWS WAF. Values are Web ACL data models
    duplicate_web_acl_groups = (
        []
    )  # Web ACL that already exists in AWS WAF. Values are Web ACL data models
    failed_web_acl_groups = (
        []
    )  # Web ACL that failed to create. Value is {str} of web acl name

    rule_source_arn = None  # arn of the source rule

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
            if rule_source_type == consts.IP_SET:
                siemplify.LOGGER.info(f"Searching {scope} IP Set {rule_source_name}")
                ip_sets = waf_client.list_ip_sets(scope=scope)
                for ip_set in ip_sets:
                    if rule_source_name == ip_set.name:
                        rule_source_arn = ip_set.arn
                        siemplify.LOGGER.info(
                            f"Found {scope} IP Set {ip_set.name} matching rule source name {rule_source_name}"
                        )
                        break
            elif rule_source_type == consts.RULE_GROUP:
                siemplify.LOGGER.info(
                    f"Searching {scope} Rule Group {rule_source_name}"
                )
                rule_groups = waf_client.list_rule_groups(scope=scope)
                for rule_group in rule_groups:
                    if rule_source_name == rule_group.name:
                        rule_source_arn = rule_group.arn
                        siemplify.LOGGER.info(
                            f"Found {scope} Rule Group {rule_group.name} matching rule source name {rule_source_name}"
                        )
                        break
            else:
                raise AWSWAFValidationException(
                    f"Failed to validate Rule Source Type {rule_source_type}"
                )

            if not rule_source_arn:
                raise AWSWAFNotFoundException(
                    f"Action wasn't able to create Web ACL. Reason: {rule_source_type} {rule_source_name} wasn't found in AWS WAF."
                )
            try:
                siemplify.LOGGER.info(
                    f"Creating {scope} web acl {web_acl_name} in AWS WAF"
                )
                created_web_acl = waf_client.create_web_acl(
                    name=web_acl_name,
                    scope=scope,
                    sampled_requests_enabled=sampled_requests_enabled,
                    cloudwatch_metrics_enabled=cloudwatch_metrics_enabled,
                    cloudwatch_metric_name=cloudwatch_metric_name,
                    tags=tags,
                    rule_source_name=rule_source_name,
                    default_action=default_action,
                    rule_group_arn=(
                        rule_source_arn
                        if rule_source_type == consts.RULE_GROUP
                        else None
                    ),
                    ip_set_arn=(
                        rule_source_arn if rule_source_type == consts.IP_SET else None
                    ),
                    ip_set_action=ip_set_action,
                    rule_priority=rule_priority,
                    description=description,
                )
                siemplify.LOGGER.info(
                    f"Successfully created {scope} web acl {web_acl_name} in AWS WAF"
                )
                json_results[consts.UNMAPPED_SCOPE.get(scope)].append(
                    created_web_acl.name
                )
                successful_web_acl_groups.append(created_web_acl)

            except (
                AWSWAFDuplicateItemException
            ) as error:  # Web ACL already exists in AWS WAF
                duplicate_web_acl_groups.append(WebACL(name=web_acl_name, scope=scope))
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

            except Exception as error:  # failed to create Web ACL in AWS WAF
                failed_web_acl_groups.append(
                    WebACL(name=web_acl_name, scope=scope)
                )  # failed Web ACLs
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

        if duplicate_web_acl_groups:
            for web_acl in duplicate_web_acl_groups:
                output_message += f"\n The Web ACL {web_acl.name} already exist in {web_acl.unmapped_scope} scope.\n"

        if (
            successful_web_acl_groups
        ):  # at least one of the rule groupes created in AWS WAF
            for web_acl in successful_web_acl_groups:
                output_message += f"\n Successfully created Web ACL {web_acl.name} in {web_acl.unmapped_scope} scope."
            result_value = "true"

        if failed_web_acl_groups:
            for web_acl in failed_web_acl_groups:
                output_message += f"\n Action was not able to create Web ACL {web_acl.name} in {web_acl.unmapped_scope} scope."

    except AWSWAFNotFoundException as error:
        output_message = f"Action wasn't able to create Web ACL. Reason: {rule_source_type} {rule_source_name} wasn't found in AWS WAF."
        siemplify.LOGGER.error(
            f"Action wasn't able to create Web ACL. Reason: {rule_source_type} {rule_source_name} wasn't found in AWS WAF."
        )
        siemplify.LOGGER.exception(error)

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Create Web ACL'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action 'Create Web ACL'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

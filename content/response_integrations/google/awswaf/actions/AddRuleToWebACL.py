from __future__ import annotations
from collections import defaultdict

from TIPCommon import extract_configuration_param, extract_action_param
from ..core import consts
from ..core.AWSWAFManager import AWSWAFManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    DEFAULT_DDL_SCOPE,
    DEFAULT_RULE_SOURCE_TYPE,
    DEFAULT_IP_SET_ACTION,
)
from ..core.exceptions import (
    AWSWAFValidationException,
    AWSWAFNotFoundException,
    AWSWAFWebACLNotFoundException,
)
from ..core.utils import load_csv_to_set, is_action_approaching_timeout, get_param_scopes

SCRIPT_NAME = "AddRuleToWebACL"


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

    web_acl_names = extract_action_param(
        siemplify, param_name="Web ACL Names", is_mandatory=True, print_value=True
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

    scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )
    param_scope = scope  # input param scope

    rule_priority = extract_action_param(
        siemplify,
        param_name="Rule Priority",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )

    ip_set_action = extract_action_param(
        siemplify,
        param_name="IP Set Action",
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_IP_SET_ACTION,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""

    # Web ACL that the rule was successfully added to. Key is Web ACL scope, value is Web ACL name
    successful_web_acls = defaultdict(list)
    duplicate_rules = defaultdict(
        list
    )  # list of rules that already exists in a Web ACL in AWS WAF. Key is Web ACL scope, value is Web ACL name

    failed_web_acls = defaultdict(
        list
    )  # list of failed Web ACLs that rule failed to be added to. Key is Web ACL scope, value is Web ACL name

    waf_web_acls = []  # list of Web ACL data models representing Web ACLs in AWS WAF
    status = EXECUTION_STATE_COMPLETED

    rule_source_arn = defaultdict(str)  # Key is Rule source scope. Value is rule ARN.

    try:
        web_acl_names = load_csv_to_set(csv=web_acl_names, param_name="Web ACL Names")
        scopes = get_param_scopes(param_scope)

        siemplify.LOGGER.info("Connecting to AWS WAF Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS WAF service")

        for scope in scopes:  # get all existing Web ACLs in specified scopes in AWS WAF
            waf_web_acls += waf_client.list_web_acls(scope=scope)

        existing_web_acls = [
            web_acl for web_acl in waf_web_acls if web_acl.name in web_acl_names
        ]  # existing Web ACLs in  AWS WAF

        missing_web_acl_names = web_acl_names.difference(
            set([web_acl.name for web_acl in existing_web_acls])
        )

        if not existing_web_acls:  # at least one web acl name must exist in AWS WAF
            raise AWSWAFWebACLNotFoundException(
                "Failed to find Web ACL names {} in the {} AWS WAF service. ".format(
                    "\n  ".join(web_acl_names),
                    consts.BOTH_SCOPE if len(scopes) == 2 else param_scope,
                )
            )

        for scope in scopes:  # find rule source in scopes
            if rule_source_type == consts.IP_SET:  # search IP Set in scope
                siemplify.LOGGER.info(f"Searching {scope} IP Set {rule_source_name}")
                ip_sets = waf_client.list_ip_sets(scope=scope)
                for ip_set in ip_sets:
                    if rule_source_name == ip_set.name:
                        rule_source_arn[scope] = ip_set.arn
                        siemplify.LOGGER.info(
                            f"Found {scope} IP Set {ip_set.name} matching rule source name {rule_source_name}"
                        )
                        break
            elif rule_source_type == consts.RULE_GROUP:  # search rule group in scope
                siemplify.LOGGER.info(
                    f"Searching {scope} Rule Group {rule_source_name}"
                )
                rule_groups = waf_client.list_rule_groups(scope=scope)
                for rule_group in rule_groups:
                    if rule_source_name == rule_group.name:
                        rule_source_arn[scope] = rule_group.arn
                        siemplify.LOGGER.info(
                            f"Found {scope} Rule Group {rule_group.name} matching rule source name {rule_source_name}"
                        )
                        break
            else:  # if rule source type is invalid raise exception
                raise AWSWAFValidationException(
                    f"Failed to validate Rule Source Type {rule_source_type}"
                )

            if not rule_source_arn[scope]:  # rule must exist in specified scope
                raise AWSWAFNotFoundException(
                    f"Action wasn't able to add rule to Web ACL. Reason: {rule_source_type} {rule_source_name} wasn't found in AWS WAF."
                )

        for (
            web_acl
        ) in existing_web_acls:  # iterate existing Web ACLs in AWF and add rule
            if is_action_approaching_timeout(siemplify):
                status = EXECUTION_STATE_TIMEDOUT
                break
            try:
                siemplify.LOGGER.info(
                    f"Retrieving existing Web ACL rules from {web_acl.scope} Web ACL {web_acl.name}"
                )

                lock_token, web_acl = waf_client.get_web_acl(
                    scope=web_acl.scope, name=web_acl.name, id=web_acl.web_acl_id
                )
                siemplify.LOGGER.info(
                    f"Successfully retrieved list of rules from {web_acl.name}"
                )
                waf_rule_list = (
                    web_acl.rules if web_acl.rules else []
                )  # rules in a web acl in WAF

                if (
                    waf_rule_list
                ):  # check if rule source name already exists in a WebACL
                    if rule_source_name in [
                        rule.name for rule in waf_rule_list
                    ]:  # check if rule exists in rule list
                        siemplify.LOGGER.info(
                            f"Rule {rule_source_name} found to be duplicate in {web_acl.scope} Web ACL {web_acl.name}"
                        )
                        duplicate_rules[web_acl.scope].append(web_acl.name)
                        continue

                siemplify.LOGGER.info(
                    f"Adding rule {rule_source_name} to Web ACL {web_acl.name}"
                )
                waf_client.update_web_acl(
                    name=web_acl.name,
                    scope=web_acl.scope,
                    rules=[rule.as_dict() for rule in waf_rule_list],
                    id=web_acl.web_acl_id,
                    sampled_requests_enabled=web_acl.sampled_requests_enabled,
                    cloudwatch_metrics_enabled=web_acl.cloudwatch_metrics_enabled,
                    cloudwatch_metric_name=web_acl.cloudwatch_metric_name,
                    rule_source_name=rule_source_name,
                    rule_group_arn=(
                        rule_source_arn[web_acl.scope]
                        if rule_source_type == consts.RULE_GROUP
                        else None
                    ),
                    ip_set_arn=(
                        rule_source_arn[web_acl.scope]
                        if rule_source_type == consts.IP_SET
                        else None
                    ),
                    ip_set_action=ip_set_action,
                    lock_token=lock_token,
                    rule_priority=rule_priority,
                    default_action=web_acl.default_action,
                )
                siemplify.LOGGER.info(
                    f"Successfully added rule {rule_source_name} to {web_acl.scope} Web ACL {web_acl.name}"
                )
                successful_web_acls[web_acl.scope].append(web_acl.name)

            except Exception as error:  # failed to update Web ACL in AWS WAF
                failed_web_acls[web_acl.scope].append(web_acl.name)
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

        for scope in scopes:  # output message for each Web ACL scope
            if successful_web_acls.get(scope):
                web_acls = successful_web_acls.get(scope)
                output_message += "\n Successfully added a rule to the following {} Web ACLs {} in AWS WAF.".format(
                    consts.UNMAPPED_SCOPE.get(scope), "\n    ".join(web_acls)
                )
                result_value = "true"

            if duplicate_rules.get(scope):
                web_acls = duplicate_rules.get(scope)
                output_message += "\n Action wasn't able to add {} rules to the Web ACL in AWS WAF. Reason: {} with name {} already exists in the following Web ACLs: \n {} - {}".format(
                    rule_source_type,
                    rule_source_type,
                    rule_source_name,
                    consts.UNMAPPED_SCOPE.get(scope),
                    "\n   ".join(web_acls),
                )
                result_value = "true"

            if failed_web_acls.get(scope):
                web_acls = failed_web_acls.get(scope)
                output_message += "\n Action was not able to add the rule to {} Rule Groups: \n {} in AWS WAF.".format(
                    consts.UNMAPPED_SCOPE.get(scope), "\n    ".join(web_acls)
                )

        if missing_web_acl_names:
            output_message += "\n Action wasn't able to find the following {} Web ACLs in AWS WAF: \n {}".format(
                consts.BOTH_SCOPE if len(scopes) == 2 else param_scope,
                "\n   ".join(missing_web_acl_names),
            )

    except AWSWAFWebACLNotFoundException as error:
        output_message = "Action didn't find the provided Web ACLs."
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)

    except AWSWAFNotFoundException as error:
        output_message = f"Action wasn't able to add rule to Web ACL. Reason: {rule_source_type} {rule_source_name} wasn't found in AWS WAF."
        siemplify.LOGGER.error(
            f"Action wasn't able to add rule to Web ACL. Reason: {rule_source_type} {rule_source_name} wasn't found in AWS WAF."
        )
        siemplify.LOGGER.exception(error)

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Add Rule To Web ACL'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action 'Add Rule To Web ACL'. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

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
from ..core.consts import INTEGRATION_NAME, DEFAULT_DDL_SCOPE
from ..core.exceptions import AWSWAFCriticalValidationException, AWSWAFNotFoundException
from ..core.utils import (
    load_csv_to_set,
    is_action_approaching_timeout,
    validate_json_object,
    get_param_scopes,
)

SCRIPT_NAME = "AddRuleToRuleGroup"


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

    rule_group_names = extract_action_param(
        siemplify, param_name="Rule Group Names", is_mandatory=True, print_value=True
    )

    scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )
    param_scope = scope  # input param scope

    rule_json = extract_action_param(
        siemplify, param_name="Rule JSON Object", is_mandatory=True, default_value=None
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""

    # Rule Groups that the rule was successfully added to. Key is Rule Group scope, value is rule group name
    successful_rule_groups = defaultdict(list)
    duplicate_rules = defaultdict(
        list
    )  # list of rules that already exists in a Rule Group in AWS WAF. Key is Rule Group scope, value is rule group name

    failed_rule_groups = defaultdict(
        list
    )  # list of failed Rule Groups that rule failed to be added. Key is Rule Group scope, value is rule group name

    waf_rule_groups = (
        []
    )  # list of Rule Group data models representing Rule Groups in AWS WAF
    status = EXECUTION_STATE_COMPLETED

    rule_name = ""  # name of the rule to add

    try:
        rule_group_names = load_csv_to_set(
            csv=rule_group_names, param_name="Rule Group Names"
        )

        if rule_json:  # validate Rule JSON Object
            siemplify.LOGGER.info("Parsing Rule JSON Object.")
            rule_json = validate_json_object(rule_json, "Rule JSON Object")
            rule_name = rule_json.get("Name")
            if rule_name is None:
                raise AWSWAFCriticalValidationException(
                    "Failed to validate Rule JSON Object"
                )
            siemplify.LOGGER.info("Successfully parsed Rule JSON Object.")

        scopes = get_param_scopes(param_scope)

        siemplify.LOGGER.info("Connecting to AWS WAF Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS WAF service")

        for (
            scope
        ) in scopes:  # get all existing Rule Groups in specified Scope in AWS WAF
            waf_rule_groups += waf_client.list_rule_groups(scope=scope)

        existing_rule_groups = [
            rule_group
            for rule_group in waf_rule_groups
            if rule_group.name in rule_group_names
        ]

        missing_rule_group_names = rule_group_names.difference(
            set([rule_group.name for rule_group in existing_rule_groups])
        )

        if (
            not existing_rule_groups
        ):  # At least one rule group name must exist on AWS WAF
            raise AWSWAFNotFoundException(
                "Failed to find Rule Group names {} in the {} AWS WAF service. ".format(
                    "\n  ".join(rule_group_names),
                    consts.BOTH_SCOPE if len(scopes) == 2 else param_scope,
                )
            )

        for (
            rule_group
        ) in (
            existing_rule_groups
        ):  # iterate all existing Rule Groups in AWS WAF to add the rule to
            if is_action_approaching_timeout(siemplify):
                status = EXECUTION_STATE_TIMEDOUT
                break
            try:
                siemplify.LOGGER.info(
                    f"Retrieving existing rule list from {rule_group.scope} Rule Group {rule_group.name}"
                )

                lock_token, rule_group = waf_client.get_rule_group(
                    scope=rule_group.scope,
                    name=rule_group.name,
                    id=rule_group.rule_group_id,
                )

                waf_rule_list = rule_group.rules if rule_group.rules else []

                if waf_rule_list:  # check if rule exists in rule list
                    if rule_name in [
                        rule.name for rule in waf_rule_list
                    ]:  # check if rule exists in rule list
                        siemplify.LOGGER.info(
                            f"Rule {rule_name} found to be duplicate in {rule_group.scope} Rule Group {rule_group.name}"
                        )
                        duplicate_rules[rule_group.scope].append(rule_group.name)
                        continue

                siemplify.LOGGER.info(
                    f"Adding rule {rule_name} to group {rule_group.name}"
                )
                waf_client.update_rule_group(
                    name=rule_group.name,
                    scope=rule_group.scope,
                    rules=[rule.as_dict() for rule in waf_rule_list]
                    + [rule_json],  # list without duplicates
                    id=rule_group.rule_group_id,
                    sampled_requests_enabled=rule_group.sampled_requests_enabled,
                    cloudwatch_metrics_enabled=rule_group.cloudwatch_metrics_enabled,
                    cloudwatch_metric_name=rule_group.cloudwatch_metric_name,
                    lock_token=lock_token,
                )
                siemplify.LOGGER.info(
                    f"Successfully added rule {rule_name} to {scope} Rule Group {rule_group.name}"
                )
                successful_rule_groups[rule_group.scope].append(rule_group.name)

            except Exception as error:  # failed to update Rule Group in AWS WAF
                failed_rule_groups[rule_group.scope].append(rule_group.name)
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

        for scope in scopes:  # output message for each Rule Group scope
            if successful_rule_groups.get(scope):
                rule_group_names = successful_rule_groups.get(scope)
                output_message += "\n Successfully added a rule to the following {} Rule Groups: \n {} in AWS WAF.".format(
                    consts.UNMAPPED_SCOPE.get(scope),
                    "\n    ".join(set(rule_group_names)),
                )
                result_value = "true"

            if duplicate_rules.get(scope):
                rule_group_names = duplicate_rules.get(scope)
                output_message += "\n Action wasn't able to add a rule to the Rule Group in AWS WAF. Reason: rule with name {} already exists in the following Rule Groups: \n {} - {}".format(
                    rule_name,
                    consts.UNMAPPED_SCOPE.get(scope),
                    "\n   ".join(set(rule_group_names)),
                )
                result_value = "true"

            if failed_rule_groups.get(scope):
                rule_group_names = failed_rule_groups.get(scope)
                output_message += "\n Action was not able to add the rule to {} Rule Groups: \n  {} in AWS WAF.".format(
                    consts.UNMAPPED_SCOPE.get(scope),
                    "\n    ".join(set(rule_group_names)),
                )

        if missing_rule_group_names:
            output_message += "\n Action wasn't able to find the following {} Rule Groups in the AWS WAF: \n {}".format(
                consts.BOTH_SCOPE if len(scopes) == 2 else param_scope,
                "\n   ".join(missing_rule_group_names),
            )

    except AWSWAFNotFoundException as error:
        siemplify.LOGGER.error("Action didn't find the provided Rule Groups.")
        siemplify.LOGGER.exception(error)
        output_message = "Action didn't find the provided Rule Groups."

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Add Rule To Rule Group'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action 'Add Rule To Rule Group'. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

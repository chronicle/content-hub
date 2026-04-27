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
from ..core.exceptions import AWSWAFNotFoundException
from ..core.utils import load_csv_to_set, is_action_approaching_timeout, get_param_scopes

SCRIPT_NAME = "Remove Rule From Rule Group"


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

    rule_name = extract_action_param(
        siemplify,
        param_name="Rule Name",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    output_message = ""

    successful_rule_groups = defaultdict(list)
    failed_rule_groups = defaultdict(list)
    sc_waf_rule_groups = defaultdict(list)
    missing = defaultdict(list)
    not_found_rules = defaultdict(list)

    waf_rule_groups = (
        []
    )  # list of Rule Group data models representing Rule Groups in AWS WAF
    status = EXECUTION_STATE_COMPLETED

    try:
        rule_group_names = load_csv_to_set(
            csv=rule_group_names, param_name="Rule Group Names"
        )

        scopes = get_param_scopes(scope)

        siemplify.LOGGER.info("Connecting to AWS WAF Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS WAF service")

        new_existing_rule_groups = defaultdict(list)
        for sc in scopes:  # get all existing Rule Groups in specified Scope in AWS WAF
            sc_rules_groups = waf_client.list_rule_groups(scope=sc)
            waf_rule_groups += sc_rules_groups
            sc_waf_rule_groups[sc] = sc_rules_groups
            new_existing_rule_groups[sc] += [
                rule_group
                for rule_group in sc_waf_rule_groups[sc]
                if rule_group.name in rule_group_names
            ]

            missing[sc] += [
                rule_gr
                for rule_gr in rule_group_names
                if rule_gr not in [rule.name for rule in new_existing_rule_groups[sc]]
            ]

        existing_rule_groups = [
            rule_group
            for rule_group in waf_rule_groups
            if rule_group.name in rule_group_names
        ]

        rule_groups = []
        for sc in scopes:
            rule_groups += new_existing_rule_groups[sc]

        if (
            not existing_rule_groups
        ):  # At least one rule group name must exist on AWS WAF
            raise AWSWAFNotFoundException(
                "Failed to find Rule Group names {} in the {} AWS WAF service. ".format(
                    "\n  ".join(rule_group_names),
                    consts.BOTH_SCOPE if len(scopes) == 2 else scope,
                )
            )

        for rule_group in existing_rule_groups:
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
                siemplify.LOGGER.info(
                    f"Successfully retrieved existing rule list from {rule_group.scope} Rule Group {rule_group.name}"
                )

                # rules in a rule group in WAF
                waf_rule_list = rule_group.rules if rule_group.rules else []
                # rules without the rule to remove
                waf_rule_list_after_remove = [
                    rule for rule in waf_rule_list if rule.name != rule_name
                ]

                # waf_rule_list = rule_group.rules if rule_group.rules else []

                if len(waf_rule_list_after_remove) != len(waf_rule_list):
                    waf_client.update_rule_group(
                        name=rule_group.name,
                        scope=rule_group.scope,
                        rules=[rule.as_dict() for rule in waf_rule_list_after_remove],
                        id=rule_group.rule_group_id,
                        sampled_requests_enabled=rule_group.sampled_requests_enabled,
                        cloudwatch_metrics_enabled=rule_group.cloudwatch_metrics_enabled,
                        cloudwatch_metric_name=rule_group.cloudwatch_metric_name,
                        lock_token=lock_token,
                    )
                    siemplify.LOGGER.info(
                        f"Successfully removed rule {rule_name} from {rule_group.scope} Rule Group {rule_group.name}"
                    )
                    successful_rule_groups[rule_group.scope].append(rule_group.name)

                else:
                    not_found_rules[rule_group.scope].append(rule_group.name)

            except Exception as error:  # failed to update Rule Group in AWS WAF
                failed_rule_groups[rule_group.scope].append(rule_group.name)
                siemplify.LOGGER.error(error)
                siemplify.LOGGER.exception(error)

        for sc in scopes:  # output message for each Rule Group scope
            if successful_rule_groups.get(sc):
                rule_group_names = successful_rule_groups.get(sc)
                output_message += "\n Successfully removed a rule from the following {} Rule Groups: \n{} in AWS WAF.".format(
                    consts.UNMAPPED_SCOPE.get(sc), "\n".join(set(rule_group_names))
                )
                result_value = True
            if failed_rule_groups.get(sc):
                rule_group_names = failed_rule_groups.get(sc)
                output_message += "\nAction was not able to remove the rule from {} Rule Groups: \n{} in AWS WAF.".format(
                    consts.UNMAPPED_SCOPE.get(sc), "\n".join(set(rule_group_names))
                )
            if not_found_rules.get(sc):
                rule_group_names = not_found_rules.get(sc)
                output_message += (
                    "\nAction wasn’t able to find the specified rule in the following"
                    " {} Rule Groups: \n{} in AWS WAF.".format(
                        consts.UNMAPPED_SCOPE.get(sc), "\n".join(set(rule_group_names))
                    )
                )
            if missing.get(sc):
                missing_rule_groups_names_str = "\n".join(missing.get(sc))
                output_message += (
                    f"\nAction wasn't able to find the following "
                    f"{sc} Rule Groups in AWS WAF: \n"
                    f"{missing_rule_groups_names_str}\n"
                )

    except AWSWAFNotFoundException as error:
        siemplify.LOGGER.error("Action didn't find the provided Rule Groups.")
        siemplify.LOGGER.exception(error)
        output_message = "Action didn't find the provided Rule Groups."

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(f"Error executing action {SCRIPT_NAME}. Reason: {error}")
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {SCRIPT_NAME}. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

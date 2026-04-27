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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, get_domain_from_entity
from ..core.consts import INTEGRATION_NAME, DEFAULT_DDL_SCOPE, HTTP_HTTPS_PROTOCOL_REGEX_WRAP
from ..core.exceptions import AWSWAFNotFoundException, AWSWAFLimitExceededException
from ..core.utils import load_csv_to_set, is_action_approaching_timeout, get_param_scopes

SCRIPT_NAME = "AddEntityToRegexPatternSet"
SUPPORTED_ENTITIES = (EntityTypes.URL, EntityTypes.ADDRESS)


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

    regex_pattern_set_names = extract_action_param(
        siemplify,
        param_name="Regex Pattern Set Names",
        is_mandatory=True,
        print_value=True,
    )

    scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )
    param_scope = scope  # input param scope
    domain_pattern = extract_action_param(
        siemplify,
        param_name="Domain Pattern",
        is_mandatory=False,
        print_value=True,
        default_value=True,
        input_type=bool,
    )
    ip_pattern = extract_action_param(
        siemplify,
        param_name="IP Pattern",
        is_mandatory=False,
        print_value=True,
        default_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "false"
    output_message = ""

    # Regexes that successfully were added to Regex Pattern set. Key is Regex set name + scope, value is list of {str} entity regexes
    successful_regex_pattern_sets = defaultdict(list)
    duplicate_regexes = defaultdict(
        list
    )  # list of regexes that already exists in AWS WAF. Key is Regex Set scoped name, value is list of {str} regexes that exist
    failed_regex_pattern_sets = defaultdict(
        list
    )  # list of regexes that failed to add to Regex Pattern Set. Key is Regex Set scoped name, value is list of {str} regexes

    waf_regex_sets = (
        []
    )  # list of Regex Pattern Set data models representing IP Sets in AWS WAF
    status = EXECUTION_STATE_COMPLETED

    regex_list = (
        []
    )  # list of regexes to add to Regex Pattern sets in AWS WAF, either with Domain/IP regex pattern or not.

    try:
        regex_set_names = load_csv_to_set(
            csv=regex_pattern_set_names, param_name="Regex Pattern Set Names"
        )
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
        ) in (
            scopes
        ):  # get all existing Regex Pattern sets in specified Scope in AWS WAF
            waf_regex_sets += waf_client.list_regex_pattern_sets(scope=scope)

        existing_regex_sets = [
            waf_regex_set
            for waf_regex_set in waf_regex_sets
            if waf_regex_set.name in regex_set_names
        ]

        missing_regex_set_names = regex_set_names.difference(
            set([regex_set.name for regex_set in existing_regex_sets])
        )

        if not existing_regex_sets:  # at least one ip set name must exist
            raise AWSWAFNotFoundException(
                "Failed to find Regex Pattern set names {} in the {} AWS WAF service. ".format(
                    "\n  ".join(regex_set_names),
                    consts.BOTH_SCOPE if len(scopes) == 2 else param_scope,
                )
            )

        for entity in siemplify.target_entities:  # process entities

            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            regex = entity.identifier

            if (
                domain_pattern and entity.entity_type == EntityTypes.URL
            ):  # wrap domain entity with HTTP/HTTPS regex
                domain = get_domain_from_entity(entity)
                regex = HTTP_HTTPS_PROTOCOL_REGEX_WRAP.format(domain)

            elif (
                ip_pattern and entity.entity_type == EntityTypes.ADDRESS
            ):  # wrap ip entity with HTTP/HTTPS regex
                regex = HTTP_HTTPS_PROTOCOL_REGEX_WRAP.format(entity.identifier.strip())

            regex_list.append(regex)
            siemplify.LOGGER.info(
                f"Finished processing entity {entity.identifier} to regex {regex}"
            )

        if regex_list:  # add processes entities to Regex Pattern sets
            for regex_set in existing_regex_sets:
                if is_action_approaching_timeout(siemplify):
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                regexes_to_add = (
                    []
                )  # regular expressions to add that do not exist in Regex Pattern Set
                try:
                    siemplify.LOGGER.info(
                        f"Retrieving existing regex list from {regex_set.scope} Regex Pattern Set {regex_set.name}"
                    )

                    lock_token, regex_set = waf_client.get_regex_pattern_set(
                        scope=regex_set.scope,
                        name=regex_set.name,
                        id=regex_set.regex_id,
                    )
                    waf_regex_list = regex_set.regex_list

                    if waf_regex_list:
                        for (
                            regex
                        ) in (
                            regex_list
                        ):  # check if regexes to add already exist in AWS WAF
                            if regex in waf_regex_list:
                                siemplify.LOGGER.info(
                                    f"Regex {regex} found to be duplicate in {regex_set.scope} Regex Pattern Set {regex_set.name}"
                                )
                                duplicate_regexes[regex_set.scoped_name].append(regex)
                            else:
                                regexes_to_add.append(regex)
                    else:
                        regexes_to_add = regex_list

                    available_num_regexes = (
                        consts.MAX_REGEX_PATTERNS_IN_REGEX_SET - len(waf_regex_list)
                    )
                    if (
                        available_num_regexes > 0
                    ):  # check if there is available capacity in Regex Pattern set
                        siemplify.LOGGER.info(
                            f"Regexes {regexes_to_add[available_num_regexes:]} exceeding available resource in AWS WAF and will not be added"
                        )
                        failed_regex_pattern_sets[
                            regex_set.scoped_name
                        ] += regexes_to_add[available_num_regexes:]
                        regexes_to_add = regexes_to_add[:available_num_regexes]
                    elif regexes_to_add:
                        raise AWSWAFLimitExceededException(
                            f"Exceeding {regex_set.scope} Regex Pattern Set {regex_set.name} available resource in AWS WAF of {consts.MAX_REGEX_PATTERNS_IN_REGEX_SET}"
                        )

                    if (
                        regexes_to_add or waf_regex_list
                    ):  # update Regex Pattern set only if the limit is not exceeded
                        waf_client.update_regex_pattern_set(
                            name=regex_set.name,
                            scope=regex_set.scope,
                            regex_list=waf_regex_list
                            + regexes_to_add,  # list without duplicates
                            id=regex_set.regex_id,
                            lock_token=lock_token,
                        )
                        siemplify.LOGGER.info(
                            f"Successfully added regexes {', '.join(regexes_to_add)} to {scope} Regex Pattern Set {regex_set.name}"
                        )
                        successful_regex_pattern_sets[
                            regex_set.scoped_name
                        ] += regexes_to_add

                except (
                    Exception
                ) as error:  # failed to create Regex Pattern Set in AWS WAF
                    failed_regex_pattern_sets[regex_set.scoped_name] += regex_list
                    siemplify.LOGGER.error(error)
                    siemplify.LOGGER.exception(error)

        for (
            regex_set
        ) in existing_regex_sets:  # output message for each Regex Pattern Set block
            if successful_regex_pattern_sets.get(regex_set.scoped_name):
                regexes = successful_regex_pattern_sets.get(regex_set.scoped_name)
                output_message += "\n Successfully added the following entity patterns to the {} Regex Pattern Set {} in AWS WAF: \n {}".format(
                    regex_set.unmapped_scope,
                    regex_set.name,
                    "\n    ".join(set(regexes)),
                )
                result_value = "true"

            if duplicate_regexes.get(regex_set.scoped_name):
                regexes = duplicate_regexes.get(regex_set.scoped_name)
                output_message += "\n The following regexes were already part of the {} Regex Pattern Set {} in AWS WAF: \n {}".format(
                    regex_set.unmapped_scope, regex_set.name, "\n   ".join(set(regexes))
                )
                result_value = "true"

            if failed_regex_pattern_sets.get(regex_set.scoped_name):
                regexes = failed_regex_pattern_sets.get(regex_set.scoped_name)
                output_message += "\n Action was not able to add the following regular expressions to {} Regex Pattern Set {} in AWS WAF: \n {}".format(
                    regex_set.unmapped_scope,
                    regex_set.name,
                    "\n    ".join(set(regexes)),
                )
                pass

            pass

        if not successful_regex_pattern_sets:
            output_message += (
                "\n No regexes were added to the provided Regex Pattern sets."
            )

        if missing_regex_set_names:
            output_message += "\n Action wasn't able to find the following {} Regex Pattern Sets in the AWS WAF: \n {}".format(
                consts.BOTH_SCOPE if len(scopes) == 2 else param_scope,
                "\n   ".join(missing_regex_set_names),
            )

    except AWSWAFNotFoundException as error:
        siemplify.LOGGER.error("Action didn't find the provided Regex Pattern sets.")
        siemplify.LOGGER.exception(error)
        output_message = "Action didn't find the provided Regex Pattern sets."

    except Exception as error:  # action failure that stops a playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Add Entity To Regex Pattern Set'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action 'Add Entity To Regex Pattern Set'. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

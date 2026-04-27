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
from ..core.consts import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, DEFAULT_DDL_SCOPE
from ..core.exceptions import AWSWAFNotFoundException
from ..core.utils import load_csv_to_set, is_action_approaching_timeout, get_param_scopes

SCRIPT_NAME = "Remove Entity From Regex Pattern Set"

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

    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = ""

    # Regex patterns that failed to remove from Regex Pattern Set. Key is Regex Pattern Set "scoped name" (name concatenated to scope).
    # Value is list of regex patterns
    failed_patterns = defaultdict(list)

    # Regex patterns that were successfully removed from Regex Pattern Set. Key is Regex Pattern Set "scoped name" (name concatenated to
    # scope). Value is list of regex patterns
    successful_patterns = defaultdict(list)

    # Regex patterns that were not found in Regex Pattern set. Key is Regex Patten Set "scoped name" (name concatenated to scope).
    # Value is list of regex patterns
    non_existed_patterns = defaultdict(list)

    existing_regex_sets = (
        []
    )  # list of Regex Pattern set that exist in WAF. Each item is an RegexSet data model

    missed_regex_names = (
        {  # list of Regex pattern sets that were not found in a particular scope in WAF
            "REGIONAL": [],
            "CLOUDFRONT": [],
        }
    )

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

        # List Regex Sets per scope
        for scope in scopes:
            regex_sets = [
                regex_set
                for regex_set in waf_client.list_regex_pattern_sets(scope=scope)
                if regex_set.name in regex_set_names
            ]
            existing_regex_sets.extend(regex_sets)
            missed_regex_names[scope] = regex_set_names.difference(
                set([regex_set.name for regex_set in regex_sets])
            )

        # At least one of the Regex Pattern Sets must exist in order to remove regex patterns from
        if not existing_regex_sets:
            raise AWSWAFNotFoundException(
                "Failed to find Regex Pattern set names {} in the {} AWS WAF service. ".format(
                    "\n  ".join(regex_set_names),
                    consts.BOTH_SCOPE if len(scopes) == 2 else param_scope,
                )
            )

        patterns_to_remove = []

        # Process entities
        for entity in siemplify.target_entities:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            # Make sure regex pattern does not contain leading/trailing whitespaces
            entity.identifier = entity.identifier.strip()

            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            regex = entity.identifier

            if (
                domain_pattern and entity.entity_type == EntityTypes.URL
            ):  # wrap domain entity with HTTP/HTTPS regex
                domain = get_domain_from_entity(entity)
                regex = consts.HTTP_HTTPS_PROTOCOL_REGEX_WRAP.format(domain)

            elif (
                ip_pattern and entity.entity_type == EntityTypes.ADDRESS
            ):  # wrap ip entity with HTTP/HTTPS regex
                regex = consts.HTTP_HTTPS_PROTOCOL_REGEX_WRAP.format(entity.identifier)

            patterns_to_remove.append(regex)
            siemplify.LOGGER.info(
                f"Entity {entity.identifier} was processed to regex: {regex}"
            )

        for regex_set in existing_regex_sets:
            if is_action_approaching_timeout(siemplify):
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                siemplify.LOGGER.info(
                    f"Retrieving existing regex list from {regex_set.scope} Regex Pattern Set {regex_set.name}"
                )

                lock_token, regex_set = waf_client.get_regex_pattern_set(
                    scope=regex_set.scope, name=regex_set.name, id=regex_set.regex_id
                )

                found_patterns_to_remove = [
                    regex
                    for regex in regex_set.regex_list
                    if regex in patterns_to_remove
                ]
                non_existed_patterns[regex_set.scoped_name].extend(
                    [
                        pattern
                        for pattern in patterns_to_remove
                        if pattern not in regex_set.regex_list
                    ]
                )

                if found_patterns_to_remove:
                    try:
                        siemplify.LOGGER.info(
                            f"Removing entity patterns {', '.join(found_patterns_to_remove)} from {regex_set.unmapped_scope}"
                            f" Regex Pattern set {regex_set.name}"
                        )
                        # Update Regex Pattern set with removed patterns
                        waf_client.update_regex_pattern_set(
                            scope=regex_set.scope,
                            name=regex_set.name,
                            regex_list=[
                                regex
                                for regex in regex_set.regex_list
                                if regex not in found_patterns_to_remove
                            ],
                            id=regex_set.regex_id,
                            lock_token=lock_token,
                        )
                        siemplify.LOGGER.info(
                            f"Successfully removed entity patterns {', '.join(found_patterns_to_remove)} from {regex_set.unmapped_scope}"
                            f" Regex Pattern set {regex_set.name}"
                        )
                        successful_patterns[regex_set.scoped_name].extend(
                            found_patterns_to_remove
                        )
                    except Exception as error:
                        failed_patterns[regex_set.scoped_name].extend(
                            found_patterns_to_remove
                        )
                        siemplify.LOGGER.info(
                            f"Failed to remove entity patterns {', '.join(found_patterns_to_remove)} from {regex_set.unmapped_scope}"
                            f" Regex Pattern set {regex_set.name}"
                        )
                        siemplify.LOGGER.exception(error)
                else:
                    siemplify.LOGGER.info(
                        f"Didn't find the following entity patterns in {regex_set.unmapped_scope} Regex Pattern Set {regex_set.name} \n"
                        f"{',   '.join(non_existed_patterns[regex_set.scoped_name])}"
                    )
            except Exception as error:
                failed_patterns[regex_set.scoped_name].extend(patterns_to_remove)
                siemplify.LOGGER.error(
                    f"Failed to get {regex_set.unmapped_scope} Regex Pattern Set {regex_set.name}. Reason: {error}"
                )
                siemplify.LOGGER.exception(error)

        # Output message for each Regex Pattern Set that were found in one of the scopes
        for regex_set in existing_regex_sets:
            if successful_patterns.get(regex_set.scoped_name):
                patterns = successful_patterns.get(regex_set.scoped_name)
                output_message += (
                    "\n\nSuccessfully removed the following entity patterns from the {} Regex Pattern Set {} in {}:\n   "
                    "{}".format(
                        regex_set.unmapped_scope,
                        regex_set.name,
                        INTEGRATION_DISPLAY_NAME,
                        "\n    ".join(patterns),
                    )
                )
                result_value = True

            if non_existed_patterns.get(regex_set.scoped_name):
                patterns = non_existed_patterns.get(regex_set.scoped_name)
                output_message += "\n\nThe following patterns were not found in the {} Regex Pattern Set {} in {}:\n   {}".format(
                    regex_set.unmapped_scope,
                    regex_set.name,
                    INTEGRATION_DISPLAY_NAME,
                    "\n   ".join(patterns),
                )
                result_value = True

            if failed_patterns.get(regex_set.scoped_name):
                patterns = failed_patterns.get(regex_set.scoped_name)
                output_message += (
                    "\n\nAction was not able to remove the following patterns from {} Regex Pattern Set {} in "
                    "{}:\n   {}".format(
                        regex_set.unmapped_scope,
                        regex_set.name,
                        INTEGRATION_DISPLAY_NAME,
                        "\n    ".join(patterns),
                    )
                )

        # Output message if no regex patterns where removed
        if not successful_patterns:
            output_message += (
                "\n\nNo patterns were removed from the provided Regex Pattern Sets."
            )

        # Output message missing regex pattern sets
        for scope, regex_pattern_names in missed_regex_names.items():
            if regex_pattern_names:
                output_message += "\n\nAction wasn't able to find the following {} Regex Pattern Sets in the {}:\n    {}".format(
                    consts.UNMAPPED_SCOPE.get(scope),
                    INTEGRATION_DISPLAY_NAME,
                    "\n   ".join(regex_pattern_names),
                )

    except AWSWAFNotFoundException as error:
        siemplify.LOGGER.error("Action didn't find the provided Regex Pattern sets.")
        siemplify.LOGGER.exception(error)
        output_message = "Action didn't find the provided Regex Pattern sets."

    except Exception as error:  # action failure that stops a playbook
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

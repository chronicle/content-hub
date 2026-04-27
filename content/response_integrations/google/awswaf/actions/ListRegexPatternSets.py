from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core import utils
from ..core.AWSWAFManager import AWSWAFManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    DEFAULT_DDL_SCOPE,
    DEFAULT_MAX_REGEX_SETS,
    MAX_REGEX_SETS,
    MIN_REGEX_PATTERN_SETS,
    UNMAPPED_SCOPE,
)

SCRIPT_NAME = "List Regex Pattern Sets"


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

    # Action parameters
    scope = extract_action_param(
        siemplify,
        param_name="Scope",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_DDL_SCOPE,
    )
    param_scope = scope  # input param scope
    max_regex_pattern_sets_to_return = extract_action_param(
        siemplify,
        param_name="Max Regex Pattern Sets To Return",
        input_type=int,
        is_mandatory=False,
        default_value=DEFAULT_MAX_REGEX_SETS,
        print_value=True,
    )

    if max_regex_pattern_sets_to_return < MIN_REGEX_PATTERN_SETS:
        siemplify.LOGGER.info(
            f"'Max Regex Pattern Sets To Return' parameter is non positive. Using default 'Max Regex Pattern Sets To Return' parameter of"
            f" {DEFAULT_MAX_REGEX_SETS}"
        )
        max_regex_pattern_sets_to_return = DEFAULT_MAX_REGEX_SETS

    if max_regex_pattern_sets_to_return > MAX_REGEX_SETS:
        siemplify.LOGGER.info(
            f"'Max Regex Pattern Sets To Return' parameter exceeding max {MAX_REGEX_SETS}. Using maximum 'Max Regex Pattern Sets To "
            f"Return' parameter of {MAX_REGEX_SETS}"
        )
        max_regex_pattern_sets_to_return = MAX_REGEX_SETS

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    json_results = {}
    failed_scopes = (
        []
    )  # Scopes which failed to list regex pattern sets from due to error
    output_message = ""

    try:
        scopes = utils.get_param_scopes(param_scope)

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_DISPLAY_NAME} Service")
        waf_client = AWSWAFManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        waf_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service"
        )

        for scope in scopes:
            try:
                siemplify.LOGGER.info(f"Retrieving regex pattern sets in scope {scope}")
                regex_sets = waf_client.list_regex_pattern_sets(
                    scope=scope, limit=max_regex_pattern_sets_to_return
                )
                siemplify.LOGGER.info(
                    f"Successfully retrieved regex pattern sets in scope {scope}"
                )

                unmapped_scope = UNMAPPED_SCOPE.get(scope)
                json_results[unmapped_scope] = [
                    regex_set.as_json() for regex_set in regex_sets
                ]
                if regex_sets:
                    result_value = True
                    siemplify.result.add_data_table(
                        f"{unmapped_scope} Regex Pattern Sets",
                        construct_csv([regex_set.as_csv() for regex_set in regex_sets]),
                    )
            except Exception as error:
                siemplify.LOGGER.error(
                    f"Failed to list regex pattern set in scope {scope}"
                )
                siemplify.LOGGER.exception(error)
                failed_scopes.append(scope)

        if len(scopes) == 2 and all(json_results.values()):
            output_message = "Successfully listed available Regex Pattern sets in Regional and Cloudfront scopes."
        elif len(scopes) == 2 and not any(json_results.values()):
            output_message = "No available Regex Pattern sets were found in Regional and Cloudfront scopes."
        else:
            for scope in scopes:
                if json_results[
                    UNMAPPED_SCOPE.get(scope)
                ]:  # If found regex pattern sets in scope
                    output_message += f"\nSuccessfully listed available Regex Pattern sets in {UNMAPPED_SCOPE.get(scope)} scope.\n"
                elif (
                    scope not in failed_scopes
                ):  # Results from scope didn't fail but there were not results
                    output_message += f"\nNo available Regex Pattern sets were found in {UNMAPPED_SCOPE.get(scope)} scope.\n"
                else:  # Failed to list regex pattern sets in one of the scopes
                    output_message += f"\nFailed to list regex pattern set in {UNMAPPED_SCOPE.get(scope)} scope.\n"

        if any(
            json_results.values()
        ):  # Add json results only if at least one of the listing succeeded
            siemplify.result.add_result_json(json_results)

    except Exception as error:
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

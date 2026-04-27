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
    DEFAULT_MAX_IP_SETS,
    MIN_IP_SETS,
    MAX_IP_SETS,
    UNMAPPED_SCOPE,
)

SCRIPT_NAME = "List IP Sets"


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
    max_ip_sets_to_return = extract_action_param(
        siemplify,
        param_name="Max IP Sets To Return",
        input_type=int,
        is_mandatory=False,
        default_value=DEFAULT_MAX_IP_SETS,
        print_value=True,
    )

    if max_ip_sets_to_return < MIN_IP_SETS:
        siemplify.LOGGER.info(
            f"'Max IP Sets To Return' parameter is non positive. Using default 'Max IP Sets To Return' parameter of"
            f" {DEFAULT_MAX_IP_SETS}"
        )
        max_ip_sets_to_return = DEFAULT_MAX_IP_SETS

    if max_ip_sets_to_return > MAX_IP_SETS:
        siemplify.LOGGER.info(
            f"'Max IP Sets To Return' parameter exceeding max {MAX_IP_SETS}. Using maximum 'Max IP Sets To "
            f"Return' parameter of {MAX_IP_SETS}"
        )
        max_ip_sets_to_return = MAX_IP_SETS

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    json_results = {}
    failed_scopes = []  # Scopes which failed to list IP sets from due to an error
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
                siemplify.LOGGER.info(f"Retrieving IP Sets in scope {scope}")
                ip_sets = waf_client.list_ip_sets(
                    scope=scope, limit=max_ip_sets_to_return
                )
                siemplify.LOGGER.info(
                    f"Successfully retrieved IP Sets in scope {scope}"
                )

                unmapped_scope = UNMAPPED_SCOPE.get(scope)
                json_results[unmapped_scope] = [ip_set.as_json() for ip_set in ip_sets]
                if ip_sets:
                    result_value = True
                    siemplify.result.add_data_table(
                        f"{unmapped_scope} IP Sets",
                        construct_csv([ip_set.as_csv() for ip_set in ip_sets]),
                    )
            except Exception as error:
                siemplify.LOGGER.error(f"Failed to list IP sets in scope {scope}")
                siemplify.LOGGER.exception(error)
                failed_scopes.append(scope)

        if len(scopes) == 2 and all(json_results.values()):
            output_message += f"\nSuccessfully listed available IP sets in Regional and CloudFront scopes.\n"
        elif len(scopes) == 2 and not any(json_results.values()):
            output_message += f"\nNo available IP sets were found in Regional and Cloudfront scopes.\n"
        else:
            for scope in scopes:
                if json_results[UNMAPPED_SCOPE.get(scope)]:  # If found IP sets in scope
                    output_message += f"\nSuccessfully listed available IP sets in {UNMAPPED_SCOPE.get(scope)} scope.\n"
                elif (
                    scope not in failed_scopes
                ):  # Results from scope didn't fail but there were not results
                    output_message += f"\nNo available IP sets were found in {UNMAPPED_SCOPE.get(scope)} scope.\n"
                else:  # Failed to list IP sets in one of the scopes
                    output_message += f"\nFailed to list IP sets in {UNMAPPED_SCOPE.get(scope)} scope.\n"

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

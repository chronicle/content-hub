from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.AWSWAFManager import AWSWAFManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    DEFAULT_DDL_SCOPE,
    MAX_WEB_ACLS,
    DEFAULT_WEB_ACLS,
    MIN_WEB_ACLS,
    CLOUDFRONT_SCOPE,
    UNMAPPED_SCOPE,
    REGIONAL_SCOPE,
)
from ..core.utils import get_param_scopes

SCRIPT_NAME = "List Web ACLs"


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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    max_web_acls_to_return = extract_action_param(
        siemplify,
        param_name="Max Web ACLs To Return",
        input_type=int,
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_WEB_ACLS,
    )

    if max_web_acls_to_return < MIN_WEB_ACLS:
        siemplify.LOGGER.info(
            f"'Max Web ACLS To Return' Should be at least {MIN_WEB_ACLS} Default value:"
            f" {DEFAULT_WEB_ACLS} will be selected"
        )
        max_web_acls_to_return = DEFAULT_WEB_ACLS

    elif max_web_acls_to_return > MAX_WEB_ACLS:
        siemplify.LOGGER.info(
            f"'Max Web ACLS To Return' Should be at most {MAX_WEB_ACLS}."
            f"will be the value"
        )
        max_web_acls_to_return = MAX_WEB_ACLS

    acls = {REGIONAL_SCOPE: [], CLOUDFRONT_SCOPE: []}

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

        siemplify.LOGGER.info(
            f"Fetching ACLs from {INTEGRATION_NAME} {max_web_acls_to_return}"
        )
        for sc in scopes:  # get all existing Web ACLs in specified scopes in AWS WAF
            acls[sc].extend(
                waf_client.list_web_acls(
                    scope=sc, max_results_to_return=max_web_acls_to_return
                )
            )
        siemplify.LOGGER.info(f"Successfully fetched ACLs from {INTEGRATION_NAME}")

        siemplify.LOGGER.info(f"Handle CloudFront scope ACLs if exists")
        #  Handle cloudfront
        acl_cloudfronts = [acl for acl in acls[CLOUDFRONT_SCOPE]]

        if acl_cloudfronts:
            json_results[UNMAPPED_SCOPE[CLOUDFRONT_SCOPE]] = [
                acl.as_json() for acl in acl_cloudfronts
            ]
            csv_cloudfront = [acl.as_csv() for acl in acl_cloudfronts]
            siemplify.result.add_data_table(
                "CloudFront Rule ACLs", construct_csv(csv_cloudfront)
            )
            result_value = True
            output_message += (
                "Successfully listed available Web ACLs in Cloudfront scope.\n"
            )

        elif CLOUDFRONT_SCOPE in scopes:
            siemplify.LOGGER.info(scopes)
            output_message += "No available Web ACLs were found in Cloudfront scope.\n"

        siemplify.LOGGER.info(f"Successfully handled CloudFront scope ACLs if exists")

        siemplify.LOGGER.info(f"Handle Regional scope ACLs if exists")
        #  Handle regional
        acl_regional = [acl for acl in acls[REGIONAL_SCOPE]]

        if acl_regional:
            json_results[UNMAPPED_SCOPE[REGIONAL_SCOPE]] = [
                acl.as_json() for acl in acl_regional
            ]
            csv_regional = [acl.as_csv() for acl in acl_regional]
            siemplify.result.add_data_table(
                "Regional Rule ACLs", construct_csv(csv_regional)
            )
            result_value = True
            output_message += (
                "Successfully listed available Web ACLs in Regional scope.\n"
            )

        elif REGIONAL_SCOPE in scopes:
            output_message += "No available Web ACLs were found in Regional scope.\n"

        siemplify.LOGGER.info(f"Successfully handled Regional scope ACLs if exists")

        if acl_cloudfronts and acl_regional:
            output_message = "Successfully listed available Web ACLs in Regional and Cloudfront scopes.\n"

        if not acl_cloudfronts and not acl_regional and len(scopes) == 2:
            output_message = (
                "No available Web ACLs were found in Regional and Cloudfront scopes."
            )

        if json_results:
            siemplify.result.add_result_json(json_results)

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action “List Web ACLs”. Reason: {error}\n"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

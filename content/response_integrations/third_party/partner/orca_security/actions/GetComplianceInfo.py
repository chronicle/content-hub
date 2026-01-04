from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    GET_COMPLIANCE_INFO_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
)
from ..core.OrcaSecurityManager import OrcaSecurityManager
from ..core.UtilsManager import convert_comma_separated_to_list, convert_list_to_comma_string


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_COMPLIANCE_INFO_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=False,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    framework_names_string = extract_action_param(
        siemplify, param_name="Framework Names", print_value=True
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Frameworks To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )
    framework_names = convert_comma_separated_to_list(framework_names_string)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = OrcaSecurityManager(
            api_root=api_root,
            api_key=api_key,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        frameworks, not_found_frameworks = manager.get_frameworks(framework_names, limit)

        if framework_names and len(not_found_frameworks) == len(framework_names):
            raise Exception(
                f"none of the provided frameworks were found in {INTEGRATION_DISPLAY_NAME}. Please check "
                f"the spelling."
            )

        if create_insight:
            siemplify.create_case_insight(
                triggered_by=INTEGRATION_NAME,
                title="Compliance Information",
                content="\n".join([framework.to_insight() for framework in frameworks]),
                entity_identifier="",
                severity=InsightSeverity.INFO,
                insight_type=InsightType.General,
            )

        siemplify.result.add_data_table(
            "Compliance Details",
            construct_csv([framework.to_table() for framework in frameworks]),
        )
        siemplify.result.add_result_json({
            "frameworks": [framework.to_json() for framework in frameworks]
        })
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully returned information about compliance in {INTEGRATION_DISPLAY_NAME}."
        )

        if not_found_frameworks:
            output_message += (
                f"\nInformation from the following frameworks wasn't found in {INTEGRATION_DISPLAY_NAME}: "
                f"{convert_list_to_comma_string(not_found_frameworks)}. Please check the spelling."
            )

    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"General error performing action {GET_COMPLIANCE_INFO_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "{GET_COMPLIANCE_INFO_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()

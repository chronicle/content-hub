from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.IronScalesManager import IronScalesManager
from ..core.IronScalesConstants import (
    PROVIDER_NAME,
    GET_MITIGATION_IMPERSONATION_DETAILS_NAME,
    DEFAULT_TIME_PERIOD,
    TIME_PERIOD_MAPPING,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_MITIGATION_IMPERSONATION_DETAILS_NAME
    siemplify.LOGGER.info("=" * 20 + " Main - Params Init " + "=" * 20)

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=False,
    )

    company_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Company ID",
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    is_partner = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Is Partner",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Parameters
    time_period = extract_action_param(
        siemplify,
        param_name="Period",
        is_mandatory=True,
        default_value=DEFAULT_TIME_PERIOD,
        print_value=True,
    )

    siemplify.LOGGER.info("=" * 20 + " Main - Started " + "=" * 20)
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = IronScalesManager(
            api_root=api_root,
            api_token=api_token,
            company_id=company_id,
            is_partner=is_partner,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        impersonation_details = manager.get_mitigation_impersonation_details(
            time_period=TIME_PERIOD_MAPPING.get(time_period)
        )

        if impersonation_details:
            output_message = (
                "Successfully fetched details of impersonation mitigations for the "
                f"{time_period}"
            )
            result_value = True
            siemplify.result.add_result_json(
                [detail.to_json() for detail in impersonation_details]
            )
        else:
            output_message = (
                "No details of impersonation mitigations were found for the "
                f"{time_period}"
            )

    except Exception as e:
        output_message = (
            'Error executing action "Get Mitigation Impersonation Details". '
            f'Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

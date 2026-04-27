from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.AzureSecurityCenterManager import AzureSecurityCenterManager
from ..core.consts import (
    INTEGRATION_NAME,
    LIST_REGULATORY_STANDARDS_SCRIPT_NAME,
    REGULATORY_STANDARD_STATES,
    DEFAULT_NUM_STANDARDS_TO_RETURN,
)
from ..core.exceptions import AzureSecurityCenterValidationException
from ..core.utils import load_csv_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_NAME} - {LIST_REGULATORY_STANDARDS_SCRIPT_NAME}"
    )
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )

    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        print_value=False,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=False,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=False,
        print_value=False,
    )
    subscription_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Subscription ID",
        print_value=True,
    )
    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant ID",
        is_mandatory=True,
        print_value=True,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    # Action parameters
    action_subscription_id = extract_action_param(
        siemplify, param_name="Subscription ID", print_value=True
    )
    state_filter = extract_action_param(
        siemplify,
        param_name="State Filter",
        default_value=None,
        is_mandatory=False,
        print_value=True,
    )
    max_standards_to_return = extract_action_param(
        siemplify,
        param_name="Max Standards To Return",
        is_mandatory=False,
        default_value=DEFAULT_NUM_STANDARDS_TO_RETURN,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED

    json_results = {}
    result_value = False

    try:
        subscription_id = action_subscription_id or subscription_id

        if not subscription_id:
            raise Exception(
                "you need to provide subscription ID in the integration configuration or action configuration."
            )

        state_filter = (
            load_csv_to_list(csv=state_filter, param_name="State Filter")
            if state_filter
            else []
        )
        state_filter = [state.lower() for state in state_filter]
        if state_filter:
            for state in state_filter:
                if state not in REGULATORY_STANDARD_STATES:
                    raise AzureSecurityCenterValidationException(
                        f"'State Filter' parameter should only contain the following values: {', '.join(REGULATORY_STANDARD_STATES)}"
                    )

        if max_standards_to_return < 0:
            siemplify.LOGGER.info(
                f"'Max Standards To Return' parameter is negative. Using default value of {DEFAULT_NUM_STANDARDS_TO_RETURN}"
            )
            max_standards_to_return = DEFAULT_NUM_STANDARDS_TO_RETURN

        manager = AzureSecurityCenterManager(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            refresh_token=refresh_token,
            verify_ssl=verify_ssl,
        )
        regulatory_standards = manager.get_regulatory_standards(
            state_filters=state_filter, limit=max_standards_to_return
        )
        if regulatory_standards:
            output_message = f"Successfully retrieved regulatory controls for the provided standards in Microsoft {INTEGRATION_NAME}"
            json_results["value"] = [
                regulatory_standard.as_json()
                for regulatory_standard in regulatory_standards
            ]
            siemplify.result.add_data_table(
                "Regulatory Standards",
                construct_csv([reg.as_csv() for reg in regulatory_standards]),
            )
            result_value = True
        else:
            output_message = (
                f"No regulatory standards were found in Microsoft {INTEGRATION_NAME}"
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f'Error executing action "{LIST_REGULATORY_STANDARDS_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{LIST_REGULATORY_STANDARDS_SCRIPT_NAME}". Reason: {e}'

    try:
        siemplify.result.add_result_json(json_results)
    except Exception as e:
        siemplify.LOGGER.error(e)
        siemplify.LOGGER.exception(e)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

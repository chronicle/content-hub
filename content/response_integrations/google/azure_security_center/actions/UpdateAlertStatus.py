from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.AzureSecurityCenterManager import AzureSecurityCenterManager
from ..core.consts import (
    INTEGRATION_NAME,
    UPDATE_ALERT_STATUS_SCRIPT_NAME,
    DEFAULT_ALERT_STATUS,
    MAPPED_ALERT_STATUS,
    PLURAL_ALERT_STATUS,
)
from ..core.utils import get_mapped_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {UPDATE_ALERT_STATUS_SCRIPT_NAME}"
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
    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=False
    )
    location = extract_action_param(
        siemplify, param_name="Location", is_mandatory=True, print_value=True
    )
    alert_status = extract_action_param(
        siemplify,
        param_name="Status",
        is_mandatory=True,
        default_value=DEFAULT_ALERT_STATUS,
        print_value=True,
    )
    alert_status_param = alert_status

    execution_state = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        subscription_id = action_subscription_id or subscription_id

        if not subscription_id:
            raise Exception(
                "you need to provide subscription ID in the integration configuration or action configuration."
            )

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
        alert_status = get_mapped_value(MAPPED_ALERT_STATUS, alert_status)
        manager.update_alert_status(
            alert_id=alert_id, location=location, alert_status=alert_status
        )
        output_message = (
            f"Successfully {get_mapped_value(PLURAL_ALERT_STATUS, alert_status_param)} alert with ID "
            f"{alert_id} in Microsoft {INTEGRATION_NAME}"
        )
        result_value = True

    except Exception as e:
        siemplify.LOGGER.error(
            f'Error executing action "{UPDATE_ALERT_STATUS_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.exception(e)
        execution_state = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f'Error executing action "{UPDATE_ALERT_STATUS_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {execution_state}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, execution_state)


if __name__ == "__main__":
    main()

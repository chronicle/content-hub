"""
Get Activity Status action for Abnormal Security Google SecOps SOAR Integration.

Checks the status of a remediation operation using the activity_log_id
returned by the Remediate Messages action.
"""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AbnormalManager import (
    AbnormalAuthenticationError,
    AbnormalConnectionError,
    AbnormalManager,
    AbnormalValidationError,
)
from ..core.constants import (
    GET_ACTIVITY_STATUS_SCRIPT_NAME,
    INTEGRATION_NAME,
    TERMINAL_STATUSES,
)


@output_handler
def main() -> None:
    """Main execution logic for the Get Activity Status action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ACTIVITY_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {GET_ACTIVITY_STATUS_SCRIPT_NAME} started")

    api_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API URL",
        is_mandatory=True,
        print_value=True,
    )
    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
    )

    activity_log_id = siemplify.extract_action_param(
        param_name="Activity Log ID",
        is_mandatory=True,
        print_value=True,
    )
    tenant_ids_raw = siemplify.extract_action_param(
        param_name="Tenant IDs",
        is_mandatory=True,
        print_value=True,
    )
    tenant_ids = [t.strip() for t in tenant_ids_raw.split(",") if t.strip()]

    result_value = False
    status = EXECUTION_STATE_FAILED

    try:
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)

        response = manager.get_activity_status(
            activity_log_id=activity_log_id,
            tenant_ids=tenant_ids,
        )

        activity_status = response.get("status", "unknown")
        siemplify.result.add_result_json(response)

        if activity_status in TERMINAL_STATUSES:
            output_message = f"Remediation activity {activity_log_id} completed with status: {activity_status}."
            result_value = activity_status in {"success", "partial_success"}
        else:
            output_message = f"Remediation activity {activity_log_id} is still in progress. Status: {activity_status}."
            result_value = True

        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(output_message)

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = f'Error executing action "{GET_ACTIVITY_STATUS_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

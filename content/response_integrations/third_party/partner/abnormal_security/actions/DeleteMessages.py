"""Delete Messages action for Abnormal Security Google SecOps SOAR Integration."""

from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.AbnormalManager import (
    AbnormalAuthenticationError,
    AbnormalConnectionError,
    AbnormalManager,
    AbnormalValidationError,
)
from ..core.constants import DELETE_MESSAGES_SCRIPT_NAME, INTEGRATION_NAME


@output_handler
def main() -> None:
    """Main execution logic for the Delete Messages action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_MESSAGES_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {DELETE_MESSAGES_SCRIPT_NAME} started")

    api_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API URL",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
    )
    source = extract_action_param(
        siemplify,
        param_name="Source",
        is_mandatory=True,
        print_value=True,
        default_value="abnormal",
    )
    messages_json = extract_action_param(
        siemplify, param_name="Messages JSON", is_mandatory=True, print_value=False
    )
    remediation_reason = extract_action_param(
        siemplify, param_name="Remediation Reason", is_mandatory=True, print_value=True
    )
    tenant_ids_raw = extract_action_param(
        siemplify, param_name="Tenant IDs", is_mandatory=False
    )
    tenant_ids = (
        [t.strip() for t in tenant_ids_raw.split(",") if t.strip()]
        if tenant_ids_raw
        else None
    )

    result_value = False
    status = EXECUTION_STATE_FAILED
    try:
        messages = json.loads(messages_json)
        if not isinstance(messages, list):
            raise AbnormalValidationError(
                "Messages JSON must be a JSON array of message objects."
            )

        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        response = manager.remediate_messages(
            action="delete",
            source=source,
            messages=messages,
            remediation_reason=remediation_reason,
            tenant_ids=tenant_ids,
        )
        activity_log_id = response.get("activity_log_id", "")
        siemplify.result.add_result_json(response)
        output_message = (
            f"Delete request submitted for {len(messages)} message(s). Activity Log ID: {activity_log_id}."
        )
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except (
        json.JSONDecodeError,
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = (
            f'Error executing action "{DELETE_MESSAGES_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

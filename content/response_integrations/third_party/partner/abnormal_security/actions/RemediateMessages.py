"""Remediate Messages action for Abnormal Security Google SecOps SOAR Integration."""

from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AbnormalManager import (
    AbnormalAuthenticationError,
    AbnormalConnectionError,
    AbnormalManager,
    AbnormalValidationError,
    parse_messages_input,
)
from ..core.constants import INTEGRATION_NAME, REMEDIATE_MESSAGES_SCRIPT_NAME


@output_handler
def main() -> None:
    """Main execution logic for the Remediate Messages action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = REMEDIATE_MESSAGES_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {REMEDIATE_MESSAGES_SCRIPT_NAME} started")

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

    action = siemplify.extract_action_param(
        param_name="Action",
        is_mandatory=True,
        print_value=True,
    )
    source = siemplify.extract_action_param(
        param_name="Source",
        is_mandatory=True,
        print_value=True,
        default_value="abnormal",
    )
    messages_json = siemplify.extract_action_param(
        param_name="Messages JSON",
        is_mandatory=True,
        print_value=False,
    )
    remediation_reason = siemplify.extract_action_param(
        param_name="Remediation Reason",
        is_mandatory=True,
        print_value=True,
    )
    tenant_ids_raw = siemplify.extract_action_param(
        param_name="Tenant IDs",
        is_mandatory=False,
    )
    tenant_ids = [t.strip() for t in tenant_ids_raw.split(",") if t.strip()] if tenant_ids_raw else None

    result_value = False
    status = EXECUTION_STATE_FAILED

    try:
        messages = parse_messages_input(messages_json)

        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        response = manager.remediate_messages(
            action=action,
            source=source,
            messages=messages,
            remediation_reason=remediation_reason,
            tenant_ids=tenant_ids,
        )

        activity_log_id = response.get("activity_log_id", "")
        siemplify.result.add_result_json(response)
        output_message = (
            f"Remediation request submitted for {len(messages)} message(s) with action "
            f"'{action}'. Activity Log ID: {activity_log_id}. "
            f"Use Get Activity Status to track completion."
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
        output_message = f'Error executing action "{REMEDIATE_MESSAGES_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

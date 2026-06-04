"""
Search Messages action for Abnormal Security Google SecOps SOAR Integration.

Searches for email messages across your organization based on threat indicators.
Results are stored as a JSON result and can be passed to Remediate Messages.
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
    INTEGRATION_NAME,
    SEARCH_MESSAGES_SCRIPT_NAME,
)


@output_handler
def main() -> None:
    """Main execution logic for the Search Messages action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_MESSAGES_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {SEARCH_MESSAGES_SCRIPT_NAME} started")

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

    start_time = siemplify.extract_action_param(
        param_name="Start Time",
        is_mandatory=True,
        print_value=True,
    )
    end_time = siemplify.extract_action_param(
        param_name="End Time",
        is_mandatory=True,
        print_value=True,
    )
    sender_email = siemplify.extract_action_param(
        param_name="Sender Email",
        is_mandatory=False,
        print_value=True,
    )
    subject = siemplify.extract_action_param(
        param_name="Subject",
        is_mandatory=False,
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
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)

        response = manager.search_messages(
            start_time=start_time,
            end_time=end_time,
            sender_email=sender_email or None,
            subject=subject or None,
            tenant_ids=tenant_ids,
        )

        # The /v1/search API returns matches under "results" (SearchResult objects),
        # each carrying the fields the remediate API requires (raw_message_id,
        # mailbox_name, native_user_id, tenant_id, subject, sender, received_time).
        # Fall back to "messages" for forward/backward compatibility.
        messages = response.get("results", response.get("messages", []))
        siemplify.result.add_result_json(response)

        output_message = f"Found {len(messages)} message(s) matching search criteria."
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(output_message)

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = f'Error executing action "{SEARCH_MESSAGES_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

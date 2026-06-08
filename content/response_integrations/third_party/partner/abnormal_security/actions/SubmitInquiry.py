"""Submit Inquiry action for Abnormal Security Google SecOps SOAR Integration."""

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
from ..core.constants import INTEGRATION_NAME, SUBMIT_INQUIRY_SCRIPT_NAME


@output_handler
def main() -> None:
    """Main execution logic for the Submit Inquiry action."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_INQUIRY_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {SUBMIT_INQUIRY_SCRIPT_NAME} started")

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

    report_type = siemplify.extract_action_param(
        param_name="Report Type",
        is_mandatory=True,
        print_value=True,
    )
    reporter = siemplify.extract_action_param(
        param_name="Reporter",
        is_mandatory=True,
        print_value=True,
    )
    subject = siemplify.extract_action_param(param_name="Subject", is_mandatory=False)
    sender_email = siemplify.extract_action_param(
        param_name="Sender Email",
        is_mandatory=False,
    )
    sender_display_name = siemplify.extract_action_param(
        param_name="Sender Display Name",
        is_mandatory=False,
    )
    recipient_email = siemplify.extract_action_param(
        param_name="Recipient Email",
        is_mandatory=False,
    )
    recipient_display_name = siemplify.extract_action_param(
        param_name="Recipient Display Name",
        is_mandatory=False,
    )
    received_time = siemplify.extract_action_param(
        param_name="Received Time",
        is_mandatory=False,
    )
    description = siemplify.extract_action_param(
        param_name="Description",
        is_mandatory=False,
    )

    result_value = False
    status = EXECUTION_STATE_FAILED
    try:
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)
        response = manager.submit_inquiry(
            report_type=report_type,
            reporter=reporter,
            subject=subject or None,
            sender_email=sender_email or None,
            sender_display_name=sender_display_name or None,
            recipient_email=recipient_email or None,
            recipient_display_name=recipient_display_name or None,
            received_time=received_time or None,
            description=description or None,
        )
        siemplify.result.add_result_json(response)
        output_message = f"Inquiry submitted as '{report_type}' by {reporter}."
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except (
        AbnormalValidationError,
        AbnormalAuthenticationError,
        AbnormalConnectionError,
        Exception,
    ) as e:
        output_message = f'Error executing action "{SUBMIT_INQUIRY_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

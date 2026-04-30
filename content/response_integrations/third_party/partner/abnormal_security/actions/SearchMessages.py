"""
Search Messages action for Abnormal Security Google SecOps SOAR Integration.

Searches for email messages across your organization based on threat indicators.
Results are stored as a JSON result and can be passed to Remediate Messages.
"""

from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

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
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_MESSAGES_SCRIPT_NAME
    siemplify.LOGGER.info(f"Action: {SEARCH_MESSAGES_SCRIPT_NAME} started")

    # Integration config
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

    # Action parameters
    start_time = extract_action_param(
        siemplify, param_name="Start Time", is_mandatory=True, print_value=True
    )
    end_time = extract_action_param(
        siemplify, param_name="End Time", is_mandatory=True, print_value=True
    )
    sender_email = extract_action_param(
        siemplify, param_name="Sender Email", is_mandatory=False, print_value=True
    )
    subject = extract_action_param(
        siemplify, param_name="Subject", is_mandatory=False, print_value=True
    )
    tenant_ids_raw = extract_action_param(
        siemplify, param_name="Tenant IDs", is_mandatory=False
    )
    tenant_ids = [t.strip() for t in tenant_ids_raw.split(",")] if tenant_ids_raw else None

    result_value = False
    status = EXECUTION_STATE_FAILED
    output_message = ""

    try:
        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)

        response = manager.search_messages(
            start_time=start_time,
            end_time=end_time,
            sender_email=sender_email or None,
            subject=subject or None,
            tenant_ids=tenant_ids,
        )

        messages = response.get("messages", [])
        siemplify.result.add_result_json(json.dumps(response))

        output_message = f"Found {len(messages)} message(s) matching search criteria."
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(output_message)

    except AbnormalValidationError as e:
        output_message = f"Invalid search parameters: {e}"
        siemplify.LOGGER.error(output_message)

    except AbnormalAuthenticationError as e:
        output_message = f"Authentication failed: {e}"
        siemplify.LOGGER.error(output_message)

    except AbnormalConnectionError as e:
        output_message = f"Connection error: {e}"
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = f"An unexpected error occurred: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}  Result: {result_value}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

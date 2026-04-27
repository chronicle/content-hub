from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TrendMicroCloudAppSecurityManager import TrendMicroCloudAppSecurityManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from ..core.constants import (
    INTEGRATION_NAME,
    MITIGATE_ACCOUNTS_ACTIONS,
    DISPLAY_INTEGRATION_NAME,
    MITIGATE_ACCOUNT_TYPES,
    MITIGATION_SUCCESS,
    MITIGATION_IN_PROGRESS,
    MITIGATION_SKIPPED,
    MITIGATION_FAILED,
    EMAIL_REGEX,
)
import json
import sys
import re


def start_operation(siemplify, trend_manager, mitigation_action, email_addresses):
    """
    Function that requests the mitigation process
    :param siemplify: SiemplifyAction object.
    :param trend_manager: TrendMicro Cloudsecurity manager object.
    :param mitigation_action: {str} Mitigation action to perform
    :param email_addresses: {List} Email Addresses to mitigate
    :return: {tuple} output message, result value, execution status
    """
    output_message = ""
    status = EXECUTION_STATE_INPROGRESS

    email_addresses_valid = [
        email for email in email_addresses if re.search(EMAIL_REGEX, email)
    ]
    email_addresses_invalid = [
        valid_email
        for valid_email in email_addresses
        if valid_email not in email_addresses_valid
    ]

    if email_addresses_valid:
        mitigation_result = trend_manager.mitigate_account(
            action_type=mitigation_action, email_addresses=email_addresses_valid
        )

        result_value = {
            "batch_id": mitigation_result.batch_id,
            "failed_emails": email_addresses_invalid,
            "successful_emails": email_addresses_valid,
        }

        result_value = json.dumps(result_value)

        if email_addresses_valid:
            output_message += (
                "\nSuccessfully initiated mitigation process for the following accounts in {}: {}. "
                "Waiting for mitigation actions to finish...".format(
                    DISPLAY_INTEGRATION_NAME,
                    ", ".join([email for email in email_addresses_valid]),
                )
            )

        if email_addresses_invalid and email_addresses_valid:
            output_message += f"\nAction wasn't able to mitigate the following accounts in {DISPLAY_INTEGRATION_NAME}: {', '.join([email for email in email_addresses_invalid])}."

    if email_addresses_invalid and not email_addresses_valid:
        result_value = False
        siemplify.LOGGER.info(
            f"Following inputs are not in valid email format: {', '.join([email for email in email_addresses_invalid])}."
        )
        output_message += f"\nNo accounts were mitigated in {DISPLAY_INTEGRATION_NAME}."
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(siemplify, trend_manager):
    """
    Function that fetches and checks the status of the mitigation
    :param siemplify: SiemplifyAction object.
    :param trend_manager: TrendMicro Cloudsecurity manager object.
    :return: {tuple} output message, result value, execution status
    """
    mitigation_status = json.loads(siemplify.extract_action_param("additional_data"))
    batch_id = mitigation_status.get("batch_id")
    email_addresses_valid = mitigation_status.get("successful_emails")

    successful_emails = []
    failed_emails = []
    all_emails_mitigated = False
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info(
        f"Checking mitigation status for mitigation of the following accounts: {', '.join([email for email in email_addresses_valid])}."
    )
    mitigation_results = trend_manager.fetch_mitigation_results(batch_id=batch_id)

    for mitigation_result in mitigation_results:

        if mitigation_result.status == MITIGATION_IN_PROGRESS:
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps(mitigation_results)
            siemplify.LOGGER.info(
                f"Mitigation of account: {mitigation_result.account_user_email} is not done yet."
            )
            output_message += "Waiting for mitigation actions to finish..."

        else:
            all_emails_mitigated = True
            if mitigation_result.status == MITIGATION_FAILED:
                failed_emails.append(mitigation_result.account_user_email)
                siemplify.LOGGER.info(
                    f"Mitigation failed for account: {mitigation_result.account_user_email}. Reason: {mitigation_result.error_message}"
                )

            if (
                mitigation_result.status == MITIGATION_SUCCESS
                or mitigation_result.status == MITIGATION_SKIPPED
            ):
                successful_emails.append(mitigation_result.account_user_email)
                if mitigation_result.status == MITIGATION_SUCCESS:
                    siemplify.LOGGER.info(
                        f"Mitigation was successful for account: {mitigation_result.account_user_email}"
                    )
                if mitigation_result.status == MITIGATION_SKIPPED:
                    siemplify.LOGGER.info(
                        f"Mitigation was successful for account {mitigation_result.account_user_email} because the mitigation process was already applied before."
                    )

    if all_emails_mitigated:
        status = EXECUTION_STATE_COMPLETED
        initially_failed_emails = mitigation_status.get("failed_emails")

        if not successful_emails:
            result_value = False
            output_message += (
                f"\nNo accounts were mitigated in {DISPLAY_INTEGRATION_NAME}."
            )

        elif successful_emails:
            result_value = True
            output_message += (
                "\nSuccessfully mitigated the following accounts in {}: {}".format(
                    DISPLAY_INTEGRATION_NAME,
                    "\n".join([email_id for email_id in successful_emails]),
                )
            )

            failed_emails = failed_emails + initially_failed_emails
            if failed_emails:
                output_message += "\nAction wasn't able to mitigate the following accounts in {}: {}".format(
                    DISPLAY_INTEGRATION_NAME,
                    "\n".join([email_id for email_id in failed_emails]),
                )

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = MITIGATE_ACCOUNTS_ACTIONS
    mode = "Main" if is_first_run else "Get Mitigation Results"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

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
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    mitigation_action = extract_action_param(
        siemplify,
        param_name="Mitigation Action",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    mitigation_action = MITIGATE_ACCOUNT_TYPES.get(mitigation_action)
    email_addresses_csv = extract_action_param(
        siemplify,
        param_name="Email Addresses",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    email_addresses = [e.strip() for e in email_addresses_csv.split(",")]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        trend_manager = TrendMicroCloudAppSecurityManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        trend_manager.test_connectivity()

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                trend_manager=trend_manager,
                mitigation_action=mitigation_action,
                email_addresses=email_addresses,
            )
        else:
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify, trend_manager=trend_manager
            )

    except Exception as e:
        output_message += (
            f"Error executing action {MITIGATE_ACCOUNTS_ACTIONS}. Reason: {e}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)

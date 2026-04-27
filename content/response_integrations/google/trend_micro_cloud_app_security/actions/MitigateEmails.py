from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TrendMicroCloudAppSecurityManager import TrendMicroCloudAppSecurityManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    MITIGATE_EMAILS_ACTION,
    DISPLAY_INTEGRATION_NAME,
    MITIGATE_EMAIL_ACTION_TYPES,
    SERVICE_TYPES,
    ACCOUNT_PROVIDER_TYPES,
    QUARANTINE_MITIGATION_ACTION,
    GMAIL_SERVICE,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = MITIGATE_EMAILS_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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

    message_ids = extract_action_param(
        siemplify,
        param_name="Message IDs",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    mitigation_action = extract_action_param(
        siemplify,
        param_name="Mitigation Action",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    service = extract_action_param(
        siemplify,
        param_name="Service",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    failed_emails = []
    successful_emails = []

    try:
        if (
            mitigation_action == QUARANTINE_MITIGATION_ACTION
            and service == GMAIL_SERVICE
        ):
            output_message += f"Error executing action {MITIGATE_EMAILS_ACTION}. Reason: You can only delete emails in gmail service."
            status = EXECUTION_STATE_FAILED
            result_value = False
            siemplify.LOGGER.info("----------------- Main - Finished -----------------")
            siemplify.LOGGER.info(
                f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
            )
            siemplify.end(output_message, result_value, status)

        service = SERVICE_TYPES.get(service)
        mitigation_action = MITIGATE_EMAIL_ACTION_TYPES.get(mitigation_action)
        account_provider = ACCOUNT_PROVIDER_TYPES.get(service)
        message_ids = [message.strip() for message in message_ids.split(",")]

        trend_manager = TrendMicroCloudAppSecurityManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        trend_manager.test_connectivity()
        for email_to_mitigate in message_ids:
            siemplify.LOGGER.info(
                f"Started processing email with id: {email_to_mitigate}"
            )

            try:
                email_details = trend_manager.get_email_details(
                    message_id=email_to_mitigate
                )
                if email_details:
                    email_details = email_details[0]
                    mailbox = email_details.mailbox
                    mail_unique_id = email_details.mail_unique_id
                    mail_message_delivery_time = (
                        email_details.mail_message_delivery_time
                    )

                    trend_manager.mitigate_email(
                        action_type=mitigation_action,
                        service=service,
                        account_provider=account_provider,
                        mailbox=mailbox,
                        mail_message_id=email_to_mitigate,
                        mail_unique_id=mail_unique_id,
                        mail_message_delivery_time=mail_message_delivery_time,
                    )

                    successful_emails.append(email_to_mitigate)
                    siemplify.LOGGER.error(
                        f"Successfully processed email with id: {email_to_mitigate}."
                    )
                else:
                    siemplify.LOGGER.error(
                        "Failed processing email with id: {}. Reason: {}".format(
                            email_to_mitigate,
                            "an email with the provided ID doesn't exist.",
                        )
                    )
                    failed_emails.append(email_to_mitigate)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed processing email with id: {email_to_mitigate}. Reason: {e}"
                )
                failed_emails.append(email_to_mitigate)

        if not successful_emails:
            result_value = False
            output_message += (
                f"\nNo emails were mitigated in {DISPLAY_INTEGRATION_NAME}."
            )

        elif successful_emails:
            output_message += (
                "\nSuccessfully mitigated the following emails in {}: {}".format(
                    DISPLAY_INTEGRATION_NAME,
                    "\n".join([email_id for email_id in successful_emails]),
                )
            )

            if failed_emails:
                output_message += "\nAction wasn’t able to mitigate the following emails in {}: {}".format(
                    DISPLAY_INTEGRATION_NAME,
                    "\n".join([email_id for email_id in failed_emails]),
                )

    except Exception as e:
        output_message += (
            f"Error executing action {MITIGATE_EMAILS_ACTION}. Reason: {e}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

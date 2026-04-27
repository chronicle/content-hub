from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.FireEyeCMConstants import (
    PROVIDER_NAME,
    DEFAULT_MAX_EMAILS_TO_RETURN,
    MIN_EMAILS_TO_RETURN,
    MAX_EMAILS_TO_RETURN,
    LIST_QUARANTINED_EMAILS_SCRIPT_NAME,
)
from ..core.FireEyeCMManager import FireEyeCMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_QUARANTINED_EMAILS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Init Integration Configurations
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=False,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Init Action Parameters
    start_time = extract_action_param(
        siemplify,
        param_name="Start Time",
        is_mandatory=False,
        default_value=None,
        print_value=True,
    )
    end_time = extract_action_param(
        siemplify,
        param_name="End Time",
        is_mandatory=False,
        default_value=None,
        print_value=True,
    )
    sender_filter = extract_action_param(
        siemplify,
        param_name="Sender Filter",
        is_mandatory=False,
        default_value=None,
        print_value=True,
    )
    subject_filter = extract_action_param(
        siemplify,
        param_name="Subject Filter",
        is_mandatory=False,
        default_value=None,
        print_value=True,
    )
    max_emails_to_return = extract_action_param(
        siemplify,
        param_name="Max Emails To Return",
        is_mandatory=False,
        input_type=int,
        default_value=DEFAULT_MAX_EMAILS_TO_RETURN,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    manager = None
    output_message = ""

    try:
        if max_emails_to_return < MIN_EMAILS_TO_RETURN:
            siemplify.LOGGER.info(
                f'"Max Email To Return" parameter provided as non-positive. Using default value of'
                f" {DEFAULT_MAX_EMAILS_TO_RETURN}"
            )
            max_emails_to_return = DEFAULT_MAX_EMAILS_TO_RETURN

        if max_emails_to_return > MAX_EMAILS_TO_RETURN:
            siemplify.LOGGER.info(
                f'"Max Email To Return" parameter must be not exceed the maximum value of {MAX_EMAILS_TO_RETURN}. Using maximum value of {MAX_EMAILS_TO_RETURN}'
            )
            max_emails_to_return = MAX_EMAILS_TO_RETURN

        manager = FireEyeCMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Listing quarantined emails in {PROVIDER_NAME}")

        quarantined_emails = manager.list_quarantined_emails(
            start_time=start_time,
            end_time=end_time,
            sender=sender_filter,
            subject_filter=subject_filter,
            limit=max_emails_to_return,
        )

        siemplify.LOGGER.info(f"Found {len(quarantined_emails)} quarantined emails.")
        if quarantined_emails:
            output_message = f"Successfully listed {PROVIDER_NAME} quarantined emails!"
            siemplify.result.add_result_json(
                [
                    quarantined_email.to_json()
                    for quarantined_email in quarantined_emails
                ]
            )
            siemplify.result.add_data_table(
                title="Quarantined Emails",
                data_table=construct_csv(
                    [
                        quarantined_email.to_csv()
                        for quarantined_email in quarantined_emails
                    ]
                ),
            )
        else:
            output_message = f"No quarantined emails were found in {PROVIDER_NAME}!"
        result_value = True

    except Exception as error:
        output_message = (
            f'Error executing action "List Quarantined Emails". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    finally:
        try:
            if manager:
                siemplify.LOGGER.info(f"Logging out from {PROVIDER_NAME}..")
                manager.logout()
                siemplify.LOGGER.info(f"Successfully logged out from {PROVIDER_NAME}")
        except Exception as error:
            siemplify.LOGGER.error(f"Logging out failed. Error: {error}")
            siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

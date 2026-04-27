from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
import re
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TrendMicroCloudAppSecurityManager import TrendMicroCloudAppSecurityManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    ENTITY_EMAIL_SEARCH_ACTION,
    SHA1_HASH_LENGTH,
    SHA256_LENGTH,
    EMAIL_REGEX,
    DISPLAY_INTEGRATION_NAME,
    MAX_DAYS_BACKWARDS,
    DEFAULT_DAYS_BACKWARDS,
    DEFAULT_NUMBER_OF_EMAILS,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENTITY_EMAIL_SEARCH_ACTION
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    final_email_results = []
    email_results = None
    unique_emails = []

    try:

        max_email_to_return = extract_action_param(
            siemplify,
            param_name="Max Emails To Return",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=DEFAULT_NUMBER_OF_EMAILS,
        )
        max_days_backwards = extract_action_param(
            siemplify,
            param_name="Max Days Backwards",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=DEFAULT_DAYS_BACKWARDS,
        )

        if max_email_to_return <= 0:
            siemplify.LOGGER.error(
                f"Max Emails To Return parameter is non positive. Using default value of {DEFAULT_NUMBER_OF_EMAILS} instead."
            )
            max_email_to_return = DEFAULT_NUMBER_OF_EMAILS

        original_max_email_to_return = max_email_to_return
        if max_days_backwards < 1:
            siemplify.LOGGER.error(
                f"Max Days Backwards parameter is non positive. Using default value of {DEFAULT_DAYS_BACKWARDS} instead."
            )
            max_days_backwards = DEFAULT_DAYS_BACKWARDS

        if max_days_backwards > MAX_DAYS_BACKWARDS:
            output_message += 'Error executing action "Entity Email Search". Reason: "Max Days Backwards" should be in range from 1 to 90.'
            result_value = False
            status = EXECUTION_STATE_FAILED
            siemplify.LOGGER.info("----------------- Main - Finished -----------------")
            siemplify.LOGGER.info(
                f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
            )
            siemplify.end(output_message, result_value, status)

        trend_manager = TrendMicroCloudAppSecurityManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )

        for entity in siemplify.target_entities:
            if max_email_to_return > 0:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                if entity.entity_type == EntityTypes.URL:
                    email_results = trend_manager.search_emails(
                        url=entity.identifier,
                        max_emails_to_return=max_email_to_return,
                        max_days_back=max_days_backwards,
                    )
                if entity.entity_type == EntityTypes.USER and re.search(
                    EMAIL_REGEX, entity.identifier
                ):
                    email_results = trend_manager.search_emails(
                        mailbox=entity.identifier,
                        max_emails_to_return=max_email_to_return,
                        max_days_back=max_days_backwards,
                    )

                if entity.entity_type == EntityTypes.FILEHASH:
                    if len(entity.identifier) == SHA1_HASH_LENGTH:
                        email_results = trend_manager.search_emails(
                            file_sha1=entity.identifier,
                            max_emails_to_return=max_email_to_return,
                            max_days_back=max_days_backwards,
                        )

                    if len(entity.identifier) == SHA256_LENGTH:
                        email_results = trend_manager.search_emails(
                            file_sha256=entity.identifier,
                            max_emails_to_return=max_email_to_return,
                            max_days_back=max_days_backwards,
                        )

                if entity.entity_type == EntityTypes.EMAILMESSAGE:
                    email_results = trend_manager.search_emails(
                        subject=entity.identifier,
                        max_emails_to_return=max_email_to_return,
                        max_days_back=max_days_backwards,
                    )

                if entity.entity_type == EntityTypes.FILENAME:
                    email_results = trend_manager.search_emails(
                        file_name=entity.identifier,
                        max_emails_to_return=max_email_to_return,
                        max_days_back=max_days_backwards,
                    )

                if entity.entity_type == EntityTypes.ADDRESS:
                    email_results = trend_manager.search_emails(
                        source_ip=entity.identifier,
                        max_emails_to_return=max_email_to_return,
                        max_days_back=max_days_backwards,
                    )

                if email_results:
                    unique_ids = 0
                    for email_result in email_results:
                        if (
                            email_result.mail_unique_id not in unique_emails
                        ):  # filtering on non-unique IDs
                            if len(final_email_results) <= max_email_to_return:
                                unique_emails.append(email_result.mail_unique_id)
                                final_email_results.append(
                                    email_result.email_value_data
                                )
                                unique_ids = unique_ids + 1

                    max_email_to_return = max_email_to_return - unique_ids
                    siemplify.LOGGER.info(
                        f"Successfully processed entity: {entity.identifier}."
                    )
                else:
                    siemplify.LOGGER.info(
                        f"Successfully processed entity: {entity.identifier} but no emails found for the given criteria."
                    )

            else:
                siemplify.LOGGER.info(
                    f"Skipped processing entity: {entity.identifier}. The limit of {original_max_email_to_return} was reached."
                )

        if final_email_results:
            siemplify.result.add_result_json(
                [email_details for email_details in final_email_results]
            )
            output_message += f"Successfully returned information about emails related to the provided entities in {DISPLAY_INTEGRATION_NAME}."
        else:
            output_message += f"No information about emails related to entities were found in {DISPLAY_INTEGRATION_NAME}."
            result_value = False

    except Exception as e:
        output_message += (
            f"Error executing action {ENTITY_EMAIL_SEARCH_ACTION}. Reason: {e}."
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

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv, convert_comma_separated_to_list

from ..core.constants import INTEGRATION_NAME, SIMPLE_ARCHIVE_SEARCH_ACTION, DEFAULT_LIMIT
from ..core.MimecastManager import MimecastManager
from ..core.UtilsManager import get_timestamps, get_integration_parameters


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SIMPLE_ARCHIVE_SEARCH_ACTION

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    integration_parameters = get_integration_parameters(siemplify)

    fields_to_return = extract_action_param(
        siemplify, param_name="Fields To Return", print_value=True, is_mandatory=True
    )
    mailboxes = extract_action_param(
        siemplify, param_name="Mailboxes", print_value=True, is_mandatory=False
    )
    from_addresses = extract_action_param(
        siemplify, param_name="From", print_value=True, is_mandatory=False
    )
    to_addresses = extract_action_param(
        siemplify, param_name="To", print_value=True, is_mandatory=False
    )
    subject = extract_action_param(
        siemplify, param_name="Subject", print_value=True, is_mandatory=False
    )
    timeframe = extract_action_param(
        siemplify, param_name="Time Frame", print_value=True, is_mandatory=False
    )
    start_time_string = extract_action_param(
        siemplify, param_name="Start Time", print_value=True, is_mandatory=False
    )
    end_time_string = extract_action_param(
        siemplify, param_name="End Time", print_value=True, is_mandatory=False
    )

    fields_to_return = convert_comma_separated_to_list(fields_to_return)
    mailboxes = convert_comma_separated_to_list(mailboxes)
    from_addresses = convert_comma_separated_to_list(from_addresses)
    to_addresses = convert_comma_separated_to_list(to_addresses)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    contains_data = False

    try:
        limit = extract_action_param(
            siemplify,
            param_name="Max Emails To Return",
            input_type=int,
            print_value=True,
            is_mandatory=False,
            default_value=50,
        )

        if limit and limit <= 0:
            siemplify.LOGGER.error(
                f'Given value of {limit} for parameter "Max Emails To Return" is non positive. '
                f"The default value {DEFAULT_LIMIT} will be used"
            )
            limit = DEFAULT_LIMIT

        start_time, end_time = get_timestamps(
            timeframe, start_time_string, end_time_string
        )

        manager = MimecastManager(
            api_root=integration_parameters.api_root,
            app_id=integration_parameters.app_id,
            app_key=integration_parameters.app_key,
            access_key=integration_parameters.access_key,
            secret_key=integration_parameters.secret_key,
            client_id=integration_parameters.client_id,
            client_secret=integration_parameters.client_secret,
            verify_ssl=integration_parameters.verify_ssl,
            siemplify=siemplify,
        )

        query = manager.build_query(
            fields=fields_to_return,
            mailboxes=mailboxes,
            from_addresses=from_addresses,
            to_addresses=to_addresses,
            subject=subject,
            start_time=start_time,
            end_time=end_time,
        )

        siemplify.LOGGER.info(f"Generated Query in XML: {query}.")

        archived_emails = manager.execute_query_with_pagination(
            xml_query=query, limit=limit
        )

        if archived_emails:

            for archived_email in archived_emails:
                if archived_email.raw_data:
                    contains_data = True

            if contains_data:

                json_result = [
                    archived_email.to_json() for archived_email in archived_emails
                ]
                data_table = [
                    archived_email.to_csv() for archived_email in archived_emails
                ]

                siemplify.result.add_result_json(json_result)
                siemplify.result.add_data_table(
                    "Results", data_table=construct_csv(data_table)
                )
                output_message = f"Successfully found archive emails for the provided criteria in {INTEGRATION_NAME}."

        if not archived_emails or not contains_data:
            output_message = f"No archive emails were found for the provided criteria in {INTEGRATION_NAME}."

    except Exception as e:
        output_message = (
            f"Error executing action {SIMPLE_ARCHIVE_SEARCH_ACTION}. Reason: {e}."
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

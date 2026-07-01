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
from typing import NoReturn

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import (
    construct_csv,
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)
from ..core import action_init
from ..core.constants import (
    DEFAULT_LIMIT,
    GET_TICKET_DETAILS_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    MAX_LIMIT,
    POSSIBLE_FIELDS,
)


TABLE_NAME = "Ticket Details"


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_TICKET_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    ticket_ids = extract_action_param(
        siemplify, param_name="Ticket IDs", is_mandatory=True, print_value=True
    )
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", print_value=True, input_type=bool
    )
    additional_fields = extract_action_param(
        siemplify, param_name="Additional Fields To Return", print_value=True
    )
    fetch_comments = extract_action_param(
        siemplify, param_name="Fetch Comments", print_value=True, input_type=bool
    )
    fetch_limit = extract_action_param(
        siemplify,
        param_name="Max Comments To Return",
        print_value=True,
        input_type=int,
        default_value=DEFAULT_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    additional_fields = [
        field.lower() for field in convert_comma_separated_to_list(additional_fields)
    ]
    ticket_ids = convert_comma_separated_to_list(ticket_ids)
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_tickets, failed_ticket_ids, json_results = [], [], []

    try:
        if fetch_limit > MAX_LIMIT or fetch_limit < 1:
            raise Exception(
                f'value for the parameter "Max Comments To Return" is invalid. Please check it. '
                f"The value should be in range from 1 to {MAX_LIMIT}."
            )

        invalid_fields = [
            field for field in additional_fields if field not in POSSIBLE_FIELDS
        ]

        if additional_fields:
            if len(invalid_fields) == len(additional_fields):
                raise Exception(
                    f'Invalid values provided for "Additional Fields To Return" parameter. '
                    f"Possible values are: {convert_list_to_comma_string(POSSIBLE_FIELDS)}."
                )
            elif invalid_fields:
                additional_fields = [
                    field for field in additional_fields if field not in invalid_fields
                ]
                siemplify.LOGGER.error(
                    f'Following values are invalid for "Additional Fields To Return" parameter: '
                    f"{convert_list_to_comma_string(invalid_fields)}."
                )

        manager = action_init.create_api_client(siemplify)
        manager.test_connection()

        for ticket_id in ticket_ids:
            siemplify.LOGGER.info(f"Started processing ticket: {ticket_id}")

            try:
                ticket = manager.get_ticket(
                    ticket_id=ticket_id,
                    additional_fields=(
                        convert_list_to_comma_string(additional_fields)
                        .replace(" ", "")
                        .replace("isread", "isRead")
                        if additional_fields
                        else ""
                    ),
                )

                ticket_json = ticket.to_json()
                if fetch_comments:
                    ticket_json["comments"] = [
                        comment.to_json()
                        for comment in manager.get_ticket_comments(
                            ticket_id, fetch_limit
                        )
                    ]

                successful_tickets.append(ticket)
                json_results.append(ticket_json)

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed processing ticket: {ticket_id}: Error is: {e}"
                )
                failed_ticket_ids.append(ticket_id)

            siemplify.LOGGER.info(f"Finished processing ticket: {ticket_id}")

        if successful_tickets:
            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table(
                TABLE_NAME,
                construct_csv([ticket.to_table() for ticket in successful_tickets]),
            )

            if create_insight:
                for ticket in successful_tickets:
                    siemplify.create_case_insight(
                        triggered_by=INTEGRATION_NAME,
                        title=f"Ticket {ticket.id}",
                        content=ticket.to_insight(),
                        entity_identifier="",
                        severity=InsightSeverity.INFO,
                        insight_type=InsightType.General,
                    )

            output_message += (
                f"Successfully returned details related to the following tickets in "
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"\n{', '.join([ticket.id for ticket in successful_tickets])}.\n\n"
            )

            if failed_ticket_ids:
                output_message += (
                    f"Action wasn't able to find details related to the following tickets in "
                    f"{INTEGRATION_DISPLAY_NAME}: {', '.join(failed_ticket_ids)}.\n"
                )
        else:
            output_message = "No tickets were found."
            result_value = False

    except Exception as error:
        output_message = (
            f"Error executing action {GET_TICKET_DETAILS_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

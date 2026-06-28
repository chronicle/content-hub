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
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from zoho_desk.core import action_init
from zoho_desk.core.constants import (
    ADD_COMMENT_TO_TICKET_SCRIPT_NAME,
    CONTENT_TYPE_MAPPING,
    INTEGRATION_DISPLAY_NAME,
    MAX_LIMIT,
    PUBLIC_VISIBILITY,
)


def add_comment(manager, ticket_id, visibility, type, text, wait_for_reply):
    """
    Add comment to ticket
    :param manager {ZohoDeskManager} ZohoDeskManager instance
    :param ticket_id {str} Ticket ID
    :param visibility {str} Specifies visibility (public/private)
    :param type {str} Type of the comment (plain text/html)
    :param text {str} Content of the comment
    :param wait_for_reply {bool} Specifies if reply should be fetched
    :return: {tuple} status, result_value, output_message
    """
    manager.add_comment(
        ticket_id=ticket_id,
        is_public=True if visibility == PUBLIC_VISIBILITY else False,
        content_type=CONTENT_TYPE_MAPPING.get(type),
        content=text,
    )
    result_value = True

    if wait_for_reply:
        status = EXECUTION_STATE_INPROGRESS
        output_message = "Waiting for a reply..."
    else:
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f'Successfully added comment "{text}" to ticket {ticket_id} '
            f"in {INTEGRATION_DISPLAY_NAME}."
        )

    return status, result_value, output_message


def get_reply(siemplify, manager, ticket_id, text):
    """
    Get comment reply
    :param siemplify: SiemplifyAction object.
    :param manager {ZohoDeskManager} ZohoDeskManager instance
    :param ticket_id {str} Ticket ID
    :param text {str} Content of the comment
    :return: {tuple} status, result_value, output_message
    """
    comments = manager.get_ticket_comments(ticket_id=ticket_id, limit=MAX_LIMIT)
    indices = [
        index for (index, comment) in enumerate(comments) if comment.content == text
    ]
    comment_index = max(indices) + 1 if indices else None
    replies = comments[comment_index:] if comment_index else []
    result_value = True

    if replies:
        first_reply = replies[0]
        siemplify.result.add_result_json(first_reply.to_json())
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f'Successfully added comment "{text}" to ticket {ticket_id} '
            f"in {INTEGRATION_DISPLAY_NAME}."
        )
    else:
        status = EXECUTION_STATE_INPROGRESS
        output_message = "Waiting for a reply..."

    return status, result_value, output_message


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_TO_TICKET_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")
    ticket_id = extract_action_param(
        siemplify, param_name="Ticket ID", is_mandatory=True, print_value=True
    )
    visibility = extract_action_param(
        siemplify, param_name="Visibility", print_value=True
    )
    type = extract_action_param(siemplify, param_name="Type", print_value=True)
    text = extract_action_param(
        siemplify, param_name="Text", is_mandatory=True, print_value=True
    )
    wait_for_reply = extract_action_param(
        siemplify,
        param_name="Wait For Reply",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = action_init.create_api_client(siemplify)

        if is_first_run:
            status, result_value, output_message = add_comment(
                manager, ticket_id, visibility, type, text, wait_for_reply
            )
        else:
            status, result_value, output_message = get_reply(
                siemplify, manager, ticket_id, text
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ADD_COMMENT_TO_TICKET_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{ADD_COMMENT_TO_TICKET_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)

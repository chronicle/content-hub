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
import json
from typing import NoReturn

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from ..core import action_init
from ..core.constants import (
    AGENT_TYPE_ASSIGNEE,
    ASSIGNEE_TYPE_MAPPING,
    CLASSIFICATION_MAPPING,
    CREATE_TICKET_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    PRIORITY_MAPPING,
    TEAM_TYPE_ASSIGNEE,
)


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_TICKET_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    title = extract_action_param(
        siemplify, param_name="Title", is_mandatory=True, print_value=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=True, print_value=True
    )
    department_name = extract_action_param(
        siemplify, param_name="Department Name", is_mandatory=True, print_value=True
    )
    contact_email = extract_action_param(
        siemplify, param_name="Contact", is_mandatory=True, print_value=True
    )
    assignee_type = extract_action_param(
        siemplify, param_name="Assignee Type", is_mandatory=False, print_value=True
    )
    assignee_name = extract_action_param(
        siemplify, param_name="Assignee Name", is_mandatory=False, print_value=True
    )
    priority = extract_action_param(
        siemplify, param_name="Priority", is_mandatory=False, print_value=True
    )
    classification = extract_action_param(
        siemplify, param_name="Classification", is_mandatory=False, print_value=True
    )
    channel = extract_action_param(
        siemplify, param_name="Channel", is_mandatory=False, print_value=True
    )
    category = extract_action_param(
        siemplify, param_name="Category", is_mandatory=False, print_value=True
    )
    sub_category = extract_action_param(
        siemplify, param_name="Sub Category", is_mandatory=False, print_value=True
    )
    due_date = extract_action_param(
        siemplify, param_name="Due Date", is_mandatory=False, print_value=True
    )
    custom_fields = extract_action_param(
        siemplify, param_name="Custom Fields", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    agent = None
    team = None

    try:
        if custom_fields:
            try:
                custom_fields = json.loads(custom_fields)
            except Exception:
                raise Exception('Unable to parse "Custom Fields" parameter as JSON.')

        assignee_type = ASSIGNEE_TYPE_MAPPING.get(assignee_type)
        priority = PRIORITY_MAPPING.get(priority)
        classification = CLASSIFICATION_MAPPING.get(classification)

        if assignee_type and not assignee_name:
            raise Exception(f'"Assignee Name" needs to be provided.')

        manager = action_init.create_api_client(siemplify)

        if assignee_type == AGENT_TYPE_ASSIGNEE:
            agents = manager.find_agent(name=assignee_name)
            if not agents:
                raise Exception(
                    f"agent {assignee_name} wasn't found in {INTEGRATION_DISPLAY_NAME}. "
                    f"Please check the spelling."
                )
            agent = agents[0]
        elif assignee_type == TEAM_TYPE_ASSIGNEE:
            teams = manager.find_team()
            team = next((item for item in teams if item.name == assignee_name), None)
            if not team:
                raise Exception(
                    f"team {assignee_name} wasn't found in {INTEGRATION_DISPLAY_NAME}. "
                    f"Please check the spelling."
                )

        departments = manager.find_department(department_name)
        if not departments:
            raise Exception(
                f"department {department_name} wasn't found in {INTEGRATION_DISPLAY_NAME}."
            )

        contacts = manager.find_contact()
        contact = next((item for item in contacts if item.email == contact_email), None)
        if not contact:
            raise Exception(
                f"contact {contact_email} wasn't found in {INTEGRATION_DISPLAY_NAME}. "
                f"Please check the spelling."
            )

        ticket = manager.create_ticket(
            title=title,
            description=description,
            department_id=departments[0].id,
            contact_id=contact.id,
            assignee_id=agent.id if agent else None,
            team_id=team.id if team else None,
            channel=channel,
            priority=priority,
            classification=classification,
            category=category,
            sub_category=sub_category,
            due_date=due_date,
            custom_fields=custom_fields,
        )
        siemplify.result.add_result_json(ticket.to_json())
        output_message = f"Successfully created a ticket with ID {ticket.id} in {INTEGRATION_DISPLAY_NAME}"
    except Exception as error:
        output_message = (
            f"Error executing action {CREATE_TICKET_SCRIPT_NAME}. Reason: {error}"
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

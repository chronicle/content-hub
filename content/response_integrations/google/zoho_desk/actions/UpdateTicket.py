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

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from ..core import action_init
from ..core.ZohoDeskApiManager import ZohoDeskApiClient
from ..core.ZohoDeskExceptions import ZohoDeskNotFound
from ..core.constants import (
    AGENT_TYPE_ASSIGNEE,
    ASSIGNEE_TYPE_MAPPING,
    MARK_STATE_MAPPING,
    READ,
    TEAM_TYPE_ASSIGNEE,
    UNREAD,
    UPDATE_TICKET_SCRIPT_NAME,
)


class UpdateTicket(Action[ZohoDeskApiClient]):

    def __init__(self) -> None:
        super().__init__(UPDATE_TICKET_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.ticket_id = extract_action_param(
            self.soar_action,
            param_name="Ticket ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.title = extract_action_param(
            self.soar_action, param_name="Title", print_value=True
        )
        self.params.description = extract_action_param(
            self.soar_action, param_name="Description", print_value=True
        )
        self.params.department_name = extract_action_param(
            self.soar_action, param_name="Department Name", print_value=True
        )
        self.params.contact_email = extract_action_param(
            self.soar_action, param_name="Contact", print_value=True
        )
        self.params.assignee_type = extract_action_param(
            self.soar_action, param_name="Assignee Type", print_value=True
        )
        self.params.assignee_name = extract_action_param(
            self.soar_action, param_name="Assignee Name", print_value=True
        )
        self.params.resolution = extract_action_param(
            self.soar_action, param_name="Resolution", print_value=True
        )
        self.params.priority = extract_action_param(
            self.soar_action, param_name="Priority", print_value=True
        )
        self.params.ticket_status = extract_action_param(
            self.soar_action, param_name="Status", print_value=True
        )
        self.params.mark_state = extract_action_param(
            self.soar_action, param_name="Mark State", print_value=True
        )
        self.params.classification = extract_action_param(
            self.soar_action, param_name="Classification", print_value=True
        )
        self.params.channel = extract_action_param(
            self.soar_action, param_name="Channel", print_value=True
        )
        self.params.category = extract_action_param(
            self.soar_action, param_name="Category", print_value=True
        )
        self.params.sub_category = extract_action_param(
            self.soar_action, param_name="Sub Category", print_value=True
        )
        self.params.due_date = extract_action_param(
            self.soar_action, param_name="Due Date", print_value=True
        )
        self.params.custom_fields = extract_action_param(
            self.soar_action, param_name="Custom Fields", print_value=True
        )

    def _validate_params(self) -> None:
        self.params.assignee_type = ASSIGNEE_TYPE_MAPPING.get(self.params.assignee_type)
        self.params.mark_state = MARK_STATE_MAPPING.get(self.params.mark_state)

        if self.params.assignee_type and not self.params.assignee_name:
            raise ValueError('"Assignee Name" needs to be provided.')

        if self.params.custom_fields:
            try:
                self.params.custom_fields = json.loads(self.params.custom_fields)
            except Exception as e:
                raise ValueError(
                    'Unable to parse "Custom Fields" parameter as JSON.'
                ) from e

    def _init_api_clients(self) -> ZohoDeskApiClient:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        department = None
        if self.params.department_name:
            department = self.api_client.find_department(self.params.department_name)
            if not department:
                raise ZohoDeskNotFound(
                    "Error executing action “Update Ticket”. "
                    f"Reason: department {self.params.department_name} "
                    "wasn't found in Zoho Desk. Please check the spelling."
                )
            department = department[0]

        contact = None
        if self.params.contact_email:
            contacts = self.api_client.find_contact()
            contact = next(
                (item for item in contacts if item.email == self.params.contact_email),
                None,
            )
            if not contact:
                raise ZohoDeskNotFound(
                    "Error executing action “Update Ticket”. "
                    f"Reason: contact {self.params.contact_email} "
                    "wasn't found in Zoho Desk. Please check the spelling."
                )

        agent, team = None, None

        if self.params.assignee_type == AGENT_TYPE_ASSIGNEE:
            agents = self.api_client.find_agent(self.params.assignee_name)
            if not agents:
                raise ZohoDeskNotFound(
                    "Error executing action “Update Ticket”. "
                    f"Reason: agent {self.params.assignee_name} "
                    "wasn't found in Zoho Desk. Please check the spelling."
                )
            agent = agents[0]

        elif self.params.assignee_type == TEAM_TYPE_ASSIGNEE:
            teams = self.api_client.find_team()
            team = next(
                (item for item in teams if item.name == self.params.assignee_name), None
            )
            if not team:
                raise ZohoDeskNotFound(
                    "Error executing action “Update Ticket”. "
                    f"Reason: team {self.params.assignee_name} "
                    "wasn't found in Zoho Desk. Please check the spelling."
                )

        if self.params.mark_state == READ:
            self.api_client.mark_ticket_as_read(self.params.ticket_id)
        elif self.params.mark_state == UNREAD:
            self.api_client.mark_ticket_as_unread(self.params.ticket_id)

        ticket = self.api_client.update_ticket(
            self.params.ticket_id,
            title=self.params.title,
            description=self.params.description,
            department=department,
            contact=contact,
            agent=agent,
            team=team,
            resolution=self.params.resolution,
            priority=self.params.priority,
            status=self.params.ticket_status,
            classification=self.params.classification,
            channel=self.params.channel,
            category=self.params.category,
            sub_category=self.params.sub_category,
            due_date=self.params.due_date,
            custom_fields=self.params.custom_fields,
        )
        self.soar_action.result.add_result_json(ticket.to_json())
        self.output_message = (
            f"Successfully updated ticket with ID {self.params.ticket_id} in Zoho Desk."
        )


def main() -> NoReturn:
    UpdateTicket().run()


if __name__ == "__main__":
    main()

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
import pathlib
import abc

import dataclasses

from TIPCommon.types import SingleJson

from zoho_desk.core.datamodels import Ticket


@dataclasses.dataclass
class ZohoDesk(abc.ABC):
    tickets: dict[str, Ticket] = dataclasses.field(default_factory=dict)

    def add_ticket(self, ticket: Ticket):
        self.tickets[ticket.id] = ticket

    def get_ticket(self, ticket_id: str) -> Ticket:
        return self.tickets[ticket_id]

    def update_ticket(
        self,
        ticket_id: str,
        raw_data: SingleJson,
        description: str,
        ticket_number: str | int,
        subject: str,
        resolution: str,
        created_time: str | int,
        status: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> None:
        """Update a ticket in mock ZohoDesk"""
        ticket = self.tickets[ticket_id]
        ticket.raw_data = raw_data
        ticket.id = ticket_id
        ticket.description = description
        ticket.ticket_number = ticket_number
        ticket.subject = subject
        ticket.resolution = resolution
        ticket.created_time = created_time
        ticket.status = status
        ticket.email = email
        ticket.last_name = first_name
        ticket.first_name = last_name

    def mark_ticket_as_spam(self, ticket_id: str) -> None:
        self.tickets[ticket_id].is_spam = True

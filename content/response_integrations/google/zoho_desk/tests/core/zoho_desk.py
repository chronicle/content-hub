from __future__ import annotations
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

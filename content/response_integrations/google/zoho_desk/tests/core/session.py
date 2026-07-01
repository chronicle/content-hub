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

from TIPCommon.types import SingleJson

from ...core.datamodels import Ticket
from ...tests.core.zoho_desk import ZohoDesk
from integration_testing import router

from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class ZohoDeskSession(MockSession[MockRequest, MockResponse, ZohoDesk]):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.update_ticket,
            self.get_ticket,
            self.mark_ticket_spam,
            check_connection,
            get_oauth_token,
        ]

    @router.get("/api/v1/tickets/[a-zA-Z0-9-]+")
    def get_ticket(self, request: MockRequest) -> MockResponse:
        """Get a ticket from Zoho Desk"""
        ticket_id: str = request.url.path.split("/")[-1]
        ticket: Ticket = self._product.get_ticket(ticket_id)
        return MockResponse(content=ticket.to_json())

    @router.patch("/api/v1/tickets/[a-zA-Z0-9-]+")
    def update_ticket(self, request: MockRequest) -> MockResponse:
        """Update a ticket in Zoho Desk"""
        ticket_id: str = request.url.path.split("/")[-1]
        parameters: SingleJson = request.kwargs["json"]

        subject: str = parameters.get("subject", "")
        description: str = parameters.get("description", "")
        ticket_number: str = parameters.get("ticketNumber", "")
        status: str = parameters.get("status", "")
        created_time: str = parameters.get("createdTime", "")
        resolution: str = parameters.get("resolution", "")
        email: str = parameters.get("email", "")
        contact: dict[str, str] = {"firstName": "Hello", "lastName": "World"}

        raw_data: SingleJson = {
            "id": ticket_id,
            "subject": subject,
            "description": description,
            "ticketNumber": ticket_number,
            "status": status,
            "createdTime": created_time,
            "resolution": resolution,
            "email": email,
            "contact": contact,
        }

        self._product.update_ticket(
            raw_data=raw_data,
            ticket_id=ticket_id,
            description=description,
            ticket_number=ticket_number,
            subject=subject,
            resolution=resolution,
            created_time=created_time,
            status=status,
            email=email,
            last_name=contact["lastName"],
            first_name=contact["firstName"],
        )

        ticket: Ticket = self._product.get_ticket(ticket_id)
        return MockResponse(content=ticket.to_json())

    @router.post("/api/v1/tickets/markSpam")
    def mark_ticket_spam(self, request: MockRequest) -> MockResponse:
        """Mark a ticket as spam by its ticket ID"""
        payload: SingleJson = request.kwargs["json"]
        ticket_id: str = payload["ids"][0]
        self._product.mark_ticket_as_spam(ticket_id)

        return MockResponse()


@router.get("/api/v1/agents")
def check_connection(_) -> MockResponse:
    return MockResponse(content={})


@router.post("/oauth/v2/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if "raise_error" in request.kwargs["data"].values():
        return MockResponse(
            content={
                "message": "Failed to authenticate to ZohoDesk",
                "errors": [{"errorMessage": "Wrong Credentials!"}],
            },
            status_code=400,
        )

    return MockResponse(
        {
            "access_token": "1000.ac445cfb678764b9da88ac5024b767c5.ac445cfb6724b76",
            "expires_in": 999_999_999_999,
        }
    )

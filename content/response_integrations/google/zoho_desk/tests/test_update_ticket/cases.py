from __future__ import annotations

import uuid

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput

TICKET_ID: str = str(uuid.uuid4())

DEFAULT_TEST_CASE_PARAMS: dict[str, str] = {
    "Ticket ID": TICKET_ID,
    "Title": "New Title",
}
DEFAULT_TEST_CASE_RESULTS: ActionOutput = ActionOutput(
    output_message=f"Successfully updated ticket with ID {TICKET_ID} in Zoho Desk.",
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=ActionJsonOutput(
        json_result={
            "contact": {"firstName": "Hello", "lastName": "World"},
            "createdTime": "",
            "description": "",
            "email": "",
            "id": TICKET_ID,
            "resolution": "",
            "status": "",
            "subject": "New Title",
            "ticketNumber": "",
        },
    ),
)

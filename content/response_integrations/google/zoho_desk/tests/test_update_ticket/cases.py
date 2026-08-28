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

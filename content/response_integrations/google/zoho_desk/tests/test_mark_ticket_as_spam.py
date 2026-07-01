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

import pytest

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from ..actions.MarkTicketAsSpam import MarkTicketAsSpam
from ..core.constants import INTEGRATION_DISPLAY_NAME
from ..core.datamodels import Ticket
from ..tests.common import (
    ACCESS_TOKEN_DB_ROW,
    CONFIG_PATH,
    DEFAULT_TICKET,
)
from ..tests.core.session import ZohoDeskSession
from ..tests.core.zoho_desk import ZohoDesk
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.requests.session import HistoryRecord
from integration_testing.set_meta import set_metadata


TICKET_ID: str = str(uuid.uuid4())
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully marked a ticket as spam in {INTEGRATION_DISPLAY_NAME}"
)

@pytest.mark.xfail(reason="issue link: b/377234451")
class TestHappyPath:

    @set_metadata(
        parameters={"Ticket ID": TICKET_ID, "Mark Contact": False},
        external_context=MockExternalContext(ACCESS_TOKEN_DB_ROW),
        integration_config_file_path=CONFIG_PATH,
    )
    def test_default_case(
        self,
        zoho_desk: ZohoDesk,
        script_session: ZohoDeskSession,
        action_output: MockActionOutput,
        external_context: MockExternalContext,
    ) -> None:
        ticket: Ticket = DEFAULT_TICKET
        ticket.id = TICKET_ID
        assert ticket.is_spam is False
        zoho_desk.add_ticket(ticket)

        MarkTicketAsSpam().run()
        updated_ticket: Ticket = zoho_desk.get_ticket(TICKET_ID)

        assert updated_ticket.is_spam is True
        assert len(script_session.request_history) == 2
        history: list[HistoryRecord] = script_session.request_history
        assert history[0].request.url.path == f"/api/v1/tickets/{TICKET_ID}"
        assert history[1].request.url.path == "/api/v1/tickets/markSpam"
        assert external_context.number_of_rows == 1
        assert action_output.results == ActionOutput(
            output_message=SUCCESS_OUTPUT_MESSAGE,
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

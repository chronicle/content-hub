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

import pathlib
import pytest

from ...actions.UpdateTicket import UpdateTicket
from ...core.datamodels import Ticket
from ...tests.common import (
    ACCESS_TOKEN_DB_ROW,
    CONFIG_PATH,
    DEFAULT_TICKET,
)
from ...tests.core.session import ZohoDeskSession
from ...tests.core.zoho_desk import ZohoDesk
from ...tests.test_update_ticket.cases import (
    DEFAULT_TEST_CASE_PARAMS,
    DEFAULT_TEST_CASE_RESULTS,
)
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


@pytest.mark.xfail(reason="issue link: b/377234451")
class TestHappyPath:

    @set_metadata(
        parameters=DEFAULT_TEST_CASE_PARAMS,
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
        ticket_id: str = DEFAULT_TEST_CASE_PARAMS["Ticket ID"]
        new_subject: str = DEFAULT_TEST_CASE_PARAMS["Title"]
        ticket.id = ticket_id
        zoho_desk.add_ticket(ticket)

        UpdateTicket().run()
        ticket: Ticket = zoho_desk.get_ticket(ticket_id)

        assert ticket.subject == new_subject
        assert len(script_session.request_history) == 1
        assert action_output.results == DEFAULT_TEST_CASE_RESULTS
        assert external_context.number_of_rows == 1

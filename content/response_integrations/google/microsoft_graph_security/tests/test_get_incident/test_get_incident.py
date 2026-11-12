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

import uuid

import pytest
from TIPCommon.base.action import ExecutionState
from microsoft_graph_security.actions.GetIncident import GetIncident
from microsoft_graph_security.core.datamodels import Incident

from microsoft_graph_security.tests.common import CONFIG_PATH, INCIDENT
from microsoft_graph_security.tests.core.microsoft_graph_security import (
    MicrosoftGraphSecurity,
)
from microsoft_graph_security.tests.core.session import (
    MicrosoftGraphSecuritySession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

INCIDENT_ID: str = str(uuid.uuid4())
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully returned information about the incident {INCIDENT_ID}"
)
INCIDENT["id"] = INCIDENT_ID
DEFAULT_INCIDENT: Incident = Incident.from_json(incident_data=INCIDENT)


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters={"Incident ID": INCIDENT_ID},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_default_case(
        self,
        microsoft_graph_security: MicrosoftGraphSecurity,
        script_session: MicrosoftGraphSecuritySession,
        action_output: MockActionOutput,
    ) -> None:
        microsoft_graph_security.add_incident(DEFAULT_INCIDENT)
        GetIncident().run()

        assert len(script_session.request_history) == 2

        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

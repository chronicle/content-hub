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

import pytest

from TIPCommon.base.action import ExecutionState
from microsoft_graph_security.actions.ListIncidents import (
    ListIncidents,
)
from microsoft_graph_security.core.datamodels import Incident
from microsoft_graph_security.tests.common import CONFIG_PATH, LIST_INCIDENTS
from microsoft_graph_security.tests.core.microsoft_graph_security import (
    MicrosoftGraphSecurity,
)
from microsoft_graph_security.tests.core.session import (
    MicrosoftGraphSecuritySession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


DEFAULT_INCIDENTS: Incident = [
    Incident.from_json(incident_data=incident) for incident in LIST_INCIDENTS["value"]
]
NO_INCIDENT = []
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully found {len(DEFAULT_INCIDENTS)} incidents for the provided "
    "criteria in Microsoft Graph."
)
NO_INCIDENT_OUTPUT_MESSAGE: str = (
    "No incidents were found for the provided criteria in Microsoft Graph."
)


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters={
            "Filter Key": "Not Specified",
            "Filter Logic": "Not Specified",
            "Filter Value": "",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_default_case(
        self,
        microsoft_graph_security: MicrosoftGraphSecurity,
        script_session: MicrosoftGraphSecuritySession,
        action_output: MockActionOutput,
    ) -> None:
        microsoft_graph_security.add_incidents(DEFAULT_INCIDENTS)
        ListIncidents().run()

        assert len(script_session.request_history) == 2

        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters={
            "Filter Key": "Id",
            "Filter Logic": "Equal",
            "Filter Value": "78345",
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_no_incident_case(
        self,
        microsoft_graph_security: MicrosoftGraphSecurity,
        script_session: MicrosoftGraphSecuritySession,
        action_output: MockActionOutput,
    ) -> None:
        microsoft_graph_security.add_incidents(NO_INCIDENT)
        ListIncidents().run()

        assert len(script_session.request_history) == 2

        assert action_output.results.output_message == NO_INCIDENT_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED

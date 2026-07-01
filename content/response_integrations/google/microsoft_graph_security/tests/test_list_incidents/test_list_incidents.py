import pytest

from TIPCommon.base.action import ExecutionState
from actions.ListIncidents import (
    ListIncidents,
)
from core.datamodels import Incident
from tests.common import CONFIG_PATH, LIST_INCIDENTS
from tests.core.microsoft_graph_security import (
    MicrosoftGraphSecurity,
)
from tests.core.session import (
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

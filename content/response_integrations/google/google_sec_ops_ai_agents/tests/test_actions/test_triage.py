from __future__ import annotations
from google_sec_ops_ai_agents.actions import triage
from google_sec_ops_ai_agents.actions.triage import \
  CONTEXT_KEY_INVESTIGATION_NAME
from google_sec_ops_ai_agents.tests import common
from google_sec_ops_ai_agents.tests.core.product import GoogleSecOpsAiAgents
from google_sec_ops_ai_agents.tests.core.session import GoogleSecOpsAiAgentsSession
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.external_context import ExternalContextRow
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from TIPCommon.data_models import DatabaseContextType

ALERT_ID = "alert-123"
INVESTIGATION_NAME = "investigations/investigation-456"


@set_metadata(
    integration_config=common.CONFIG,
)
def test_triage_first_run(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
  # Mock the API responses
  google_chronicle_ai_agents.cleanup_investigations()
  google_chronicle_ai_agents.add_investigations(
      ALERT_ID, []
  )  # No existing investigations
  google_chronicle_ai_agents.add_triggered_investigation(
      ALERT_ID, {"name": INVESTIGATION_NAME}
  )
  set_is_first_run_to_true()
  triage.main()

  assert (
      len(script_session.request_history) == 3
  )  # GetAlertDetails + list_investigations + trigger_investigation
  assert action_output.results == ActionOutput(
      output_message=(
          f"Successfully triggered investigation: {INVESTIGATION_NAME}"
      ),
      result_value=True,
      json_output=None,
      execution_state=ExecutionState.IN_PROGRESS,
  )


INVESTIGATION_CONTEXT: list[ExternalContextRow[str]] = [
    ExternalContextRow(
        context_type=DatabaseContextType.ALERT,
        identifier="Phishing email detector3wM/eL7XV3hdthDGI3TUCzTZrm+gwID5DaLrxaRCT6U=_c8f65349-8519-4d4b-8aca-3e0075e61003",
        property_key=CONTEXT_KEY_INVESTIGATION_NAME,
        property_value=INVESTIGATION_NAME,
    )
]

@set_metadata(
    integration_config=common.CONFIG,
    external_context=MockExternalContext(INVESTIGATION_CONTEXT),
)
def test_triage_polling_run_completed(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
  # Mock the API response
  investigation_data = {
      "name": INVESTIGATION_NAME,
      "status": "STATUS_COMPLETED_SUCCESS",
      "summary": "* \n\n* A **SentinelOne** alert detected an outbound TCPv4 "
                 "connection",
      "verdict": "TRUE_POSITIVE",
      "confidence": "HIGH_CONFIDENCE"
  }
  google_chronicle_ai_agents.add_investigation_status(
      INVESTIGATION_NAME, investigation_data
  )

  triage.main()

  assert action_output.results == ActionOutput(
      output_message=(
          "Investigation Summary: True Positive (High Confidence)"
      ),
      result_value=True,
      execution_state=ExecutionState.COMPLETED,
      json_output=ActionJsonOutput(json_result={"agent_raw_data":investigation_data,
                     "verdict":"True Positive",
                     "confidence": "High Confidence",
                     }),
  )

from proof_point_tap.actions import GetThreatForensics
from proof_point_tap.tests import common
from proof_point_tap.tests.core.product import ProofPointTAP
from proof_point_tap.tests.core.session import ProofPointTAPSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully returned forensics for the following threats in Proofpoint TAP: abc"
)
NO_FORENSICS_FOUND_MESSAGE: str = (
    "No forensics were found for the provided threats in Proofpoint TAP."
)

DEFAULT_PARAMETERS: dict[str, str] = {"Threat ID": "abc", "Max Results To Return": 1}


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_get_threat_forensics_action_no_forensics_success(
    proof_point_tap: ProofPointTAP,
    script_session: ProofPointTAPSession,
    action_output: MockActionOutput,
) -> None:
    proof_point_tap.add_threat_forensics(common.PING_DATA)
    GetThreatForensics.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == NO_FORENSICS_FOUND_MESSAGE
    assert action_output.results.result_value is True


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_get_threat_forensics_action_success(
    proof_point_tap: ProofPointTAP,
    script_session: ProofPointTAPSession,
    action_output: MockActionOutput,
) -> None:
    proof_point_tap.add_threat_forensics(common.THREAT_FORENSICS)
    GetThreatForensics.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True

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

from TIPCommon.base.action import ExecutionState

from mitre_attck.actions import GetTechniquesMitigations
from mitre_attck.tests.common import (
    ATTACK_PATTERN_EXTERNAL_ID,
    ATTACK_PATTERN_ID,
    ATTACK_PATTERN_NAME,
    CONFIG,
)
from mitre_attck.tests.core.session import MitreAttckSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


# ---------------------------------------------------------------------------
# Parameters
# GetTechniquesMitigations is the multi-technique variant of GetMitigations.
# attack-pattern--001 has one "mitigates" relationship → course-of-action--001.
# attack-pattern--002 has none.
# ---------------------------------------------------------------------------
PARAMS_BY_ID_HAS_MITIGATIONS: dict = {
    "Technique ID": ATTACK_PATTERN_ID,
    "Identifier Type": "Attack ID",
    "Max Mitigations to Return": "20",
}
PARAMS_BY_EXTERNAL_ID: dict = {
    "Technique ID": ATTACK_PATTERN_EXTERNAL_ID,
    "Identifier Type": "External Attack ID",
    "Max Mitigations to Return": "20",
}
PARAMS_BY_NAME: dict = {
    "Technique ID": ATTACK_PATTERN_NAME,
    "Identifier Type": "Attack Name",
    "Max Mitigations to Return": "20",
}
PARAMS_NO_MITIGATIONS: dict = {
    "Technique ID": "attack-pattern--002",
    "Identifier Type": "Attack ID",
    "Max Mitigations to Return": "20",
}
PARAMS_MULTI: dict = {
    # comma-separated: one hit + one miss
    "Technique ID": f"{ATTACK_PATTERN_ID}, attack-pattern--002",
    "Identifier Type": "Attack ID",
    "Max Mitigations to Return": "20",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@set_metadata(parameters=PARAMS_BY_ID_HAS_MITIGATIONS, integration_config=CONFIG)
def test_get_techniques_mitigations_by_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED with mitigation data for a technique ID that has mitigations."""
    GetTechniquesMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert "Successfully retrieved mitigations" in result.output_message
    assert result.json_output is not None


@set_metadata(parameters=PARAMS_BY_EXTERNAL_ID, integration_config=CONFIG)
def test_get_techniques_mitigations_by_external_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED when queried by External Attack ID."""
    GetTechniquesMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_BY_NAME, integration_config=CONFIG)
def test_get_techniques_mitigations_by_name_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED when queried by Attack Name."""
    GetTechniquesMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_NO_MITIGATIONS, integration_config=CONFIG)
def test_get_techniques_mitigations_no_results(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """result_value is False and output says 'No mitigations were found'."""
    GetTechniquesMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is False
    assert "No mitigations were found" in result.output_message


@set_metadata(parameters=PARAMS_MULTI, integration_config=CONFIG)
def test_get_techniques_mitigations_partial_match(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """One technique has mitigations, one does not — partial success messages present."""
    GetTechniquesMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert "Successfully retrieved mitigations" in result.output_message
    assert "wasn't able to find mitigations" in result.output_message


@set_metadata(parameters=PARAMS_BY_ID_HAS_MITIGATIONS, integration_config=CONFIG)
def test_get_techniques_mitigations_api_error(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
    mitre_product,
) -> None:
    """Unhandled HTTP failure is caught; action returns FAILED with an error message."""
    with mitre_product.fail_requests():
        GetTechniquesMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.FAILED
    assert 'Error executing action "Get Techniques Mitigations"' in result.output_message


@set_metadata(parameters=PARAMS_BY_ID_HAS_MITIGATIONS, integration_config=CONFIG)
def test_get_techniques_mitigations_connectivity_check(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
    mitre_product,
) -> None:
    """GetTechniquesMitigations calls test_connectivity first; empty response → FAILED.

    ISSUE FINDER: Unlike GetMitigations, this action explicitly calls
    manager.test_connectivity() and short-circuits to EXECUTION_STATE_FAILED if it
    returns False.  An empty dict ``{}`` returned by the endpoint causes this path.
    """
    mitre_product.set_attack_data({})

    GetTechniquesMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.FAILED
    assert "Unable to connect to MitreAttack" in result.output_message

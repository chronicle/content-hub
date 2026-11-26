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

from mitre_attck.actions import GetMitigations
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
# The mock STIX bundle has relationship--002: course-of-action--001 "mitigates"
# attack-pattern--001.  Querying attack-pattern--001 returns M1022.
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
    # attack-pattern--002 has no "mitigates" relationship in the mock bundle
    "Technique ID": "attack-pattern--002",
    "Identifier Type": "Attack ID",
    "Max Mitigations to Return": "20",
}
PARAMS_LIMIT_ONE: dict = {
    "Technique ID": ATTACK_PATTERN_ID,
    "Identifier Type": "Attack ID",
    "Max Mitigations to Return": "1",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@set_metadata(parameters=PARAMS_BY_ID_HAS_MITIGATIONS, integration_config=CONFIG)
def test_get_mitigations_by_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED with mitigation data when the technique has 'mitigates' rels."""
    GetMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert "Found mitigations" in result.output_message
    assert result.json_output is not None


@set_metadata(parameters=PARAMS_BY_EXTERNAL_ID, integration_config=CONFIG)
def test_get_mitigations_by_external_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED when queried by External Attack ID."""
    GetMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_BY_NAME, integration_config=CONFIG)
def test_get_mitigations_by_name_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED when queried by Attack Name."""
    GetMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_NO_MITIGATIONS, integration_config=CONFIG)
def test_get_mitigations_no_results(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED with result_value False when there are no mitigations."""
    GetMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is False
    assert "Didn't find any mitigations" in result.output_message


@set_metadata(parameters=PARAMS_LIMIT_ONE, integration_config=CONFIG)
def test_get_mitigations_respects_limit(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Max Mitigations to Return is forwarded to get_all_where_id_in correctly."""
    GetMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_BY_ID_HAS_MITIGATIONS, integration_config=CONFIG)
def test_get_mitigations_api_error(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
    mitre_product,
) -> None:
    """Unhandled HTTP failure is caught; action returns FAILED with an error message."""
    with mitre_product.fail_requests():
        GetMitigations.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.FAILED
    assert 'Error executing action "Get Mitigations"' in result.output_message

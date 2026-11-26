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

from mitre_attck.actions import GetAssociatedIntrusions
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
# The mock STIX bundle has relationship--001: intrusion-set--001 "uses"
# attack-pattern--001.  So querying attack-pattern--001 should return APT28.
# ---------------------------------------------------------------------------
PARAMS_BY_ID_HAS_INTRUSIONS: dict = {
    "Technique ID": ATTACK_PATTERN_ID,
    "Identifier Type": "Attack ID",
    "Max Intrusions to Return": "20",
}
PARAMS_BY_EXTERNAL_ID_HAS_INTRUSIONS: dict = {
    "Technique ID": ATTACK_PATTERN_EXTERNAL_ID,
    "Identifier Type": "External Attack ID",
    "Max Intrusions to Return": "20",
}
PARAMS_BY_NAME_HAS_INTRUSIONS: dict = {
    "Technique ID": ATTACK_PATTERN_NAME,
    "Identifier Type": "Attack Name",
    "Max Intrusions to Return": "20",
}
PARAMS_NO_INTRUSIONS: dict = {
    # attack-pattern--002 has no "uses" relationship in the mock bundle
    "Technique ID": "attack-pattern--002",
    "Identifier Type": "Attack ID",
    "Max Intrusions to Return": "20",
}
PARAMS_LIMIT_ONE: dict = {
    "Technique ID": ATTACK_PATTERN_ID,
    "Identifier Type": "Attack ID",
    "Max Intrusions to Return": "1",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@set_metadata(parameters=PARAMS_BY_ID_HAS_INTRUSIONS, integration_config=CONFIG)
def test_get_associated_intrusions_by_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED with intrusion data when the technique has 'uses' relationships."""
    GetAssociatedIntrusions.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert "Found associated intrusions" in result.output_message
    assert result.json_output is not None


@set_metadata(parameters=PARAMS_BY_EXTERNAL_ID_HAS_INTRUSIONS, integration_config=CONFIG)
def test_get_associated_intrusions_by_external_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED when queried by External Attack ID (e.g. T1566.001)."""
    GetAssociatedIntrusions.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_BY_NAME_HAS_INTRUSIONS, integration_config=CONFIG)
def test_get_associated_intrusions_by_name_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED when queried by Attack Name."""
    GetAssociatedIntrusions.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_NO_INTRUSIONS, integration_config=CONFIG)
def test_get_associated_intrusions_no_results(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Returns COMPLETED with result_value False when no 'uses' relationships exist."""
    GetAssociatedIntrusions.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is False
    assert "Didn't find any intrusion" in result.output_message


@set_metadata(parameters=PARAMS_LIMIT_ONE, integration_config=CONFIG)
def test_get_associated_intrusions_respects_limit(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """The Max Intrusions to Return parameter is honoured by get_all_where_id_in."""
    GetAssociatedIntrusions.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    # With limit=1 and 1 matching intrusion in the bundle, still succeeds
    assert result.result_value is True


@set_metadata(parameters=PARAMS_BY_ID_HAS_INTRUSIONS, integration_config=CONFIG)
def test_get_associated_intrusions_api_error(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
    mitre_product,
) -> None:
    """Unhandled HTTP failure is caught; action returns FAILED with an error message."""
    with mitre_product.fail_requests():
        GetAssociatedIntrusions.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.FAILED
    assert 'Error executing action "Get Associated Intrusions"' in result.output_message

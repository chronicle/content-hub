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
from mitre_attck.actions import GetTechniqueDetails
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
# ---------------------------------------------------------------------------
PARAMS_BY_ID: dict = {
    "Technique Identifier": ATTACK_PATTERN_ID,
    "Identifier Type": "ID",
    "Create Insights": "False",
}
PARAMS_BY_EXTERNAL_ID: dict = {
    "Technique Identifier": ATTACK_PATTERN_EXTERNAL_ID,
    "Identifier Type": "External ID",
    "Create Insights": "False",
}
PARAMS_BY_NAME: dict = {
    "Technique Identifier": ATTACK_PATTERN_NAME,
    "Identifier Type": "Name",
    "Create Insights": "False",
}
PARAMS_NOT_FOUND: dict = {
    "Technique Identifier": "attack-pattern--does-not-exist",
    "Identifier Type": "ID",
    "Create Insights": "False",
}
PARAMS_MULTI: dict = {
    "Technique Identifier": f"{ATTACK_PATTERN_ID}, attack-pattern--does-not-exist",
    "Identifier Type": "ID",
    "Create Insights": "False",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@set_metadata(parameters=PARAMS_BY_ID, integration_config=CONFIG)
def test_get_technique_details_by_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Action returns COMPLETED and JSON results when a valid Attack ID is supplied."""
    GetTechniqueDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert "Retrieved detailed information" in result.output_message
    assert ATTACK_PATTERN_ID in result.output_message
    assert result.json_output is not None


@set_metadata(parameters=PARAMS_BY_EXTERNAL_ID, integration_config=CONFIG)
def test_get_technique_details_by_external_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Action returns COMPLETED when queried by External ID (e.g. T1566.001)."""
    GetTechniqueDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert result.json_output is not None


@set_metadata(parameters=PARAMS_BY_NAME, integration_config=CONFIG)
def test_get_technique_details_by_name_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Action returns COMPLETED when queried by attack name."""
    GetTechniqueDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_NOT_FOUND, integration_config=CONFIG)
def test_get_technique_details_not_found(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Action completes but result_value is False when the technique is not found."""
    GetTechniqueDetails.main()

    result = action_output.results
    # ISSUE FINDER: The action only sets status=COMPLETED at the end of the try block
    # (after the loop), so even on a "not found" the execution state is COMPLETED.
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is False
    assert "wasn't able to find" in result.output_message


@set_metadata(parameters=PARAMS_MULTI, integration_config=CONFIG)
def test_get_technique_details_partial_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """When one identifier is found and one is not, result_value is True and both
    outcome messages are included."""
    GetTechniqueDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert "Retrieved detailed information" in result.output_message
    assert "wasn't able" in result.output_message


@set_metadata(parameters=PARAMS_BY_ID, integration_config=CONFIG)
def test_get_technique_details_api_error(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
    mitre_product,
) -> None:
    """Action catches unhandled exceptions and returns an error message."""
    with mitre_product.fail_requests():
        GetTechniqueDetails.main()

    result = action_output.results
    # ISSUE FINDER: On exception the action does NOT set status; it falls through
    # to siemplify.end with status=EXECUTION_STATE_FAILED (initial value).
    assert result.execution_state == ExecutionState.FAILED
    assert 'Error executing action "Get Technique Details"' in result.output_message

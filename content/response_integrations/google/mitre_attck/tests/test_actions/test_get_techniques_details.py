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

from mitre_attck.actions import GetTechniquesDetails
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
}
PARAMS_BY_EXTERNAL_ID: dict = {
    "Technique Identifier": ATTACK_PATTERN_EXTERNAL_ID,
    "Identifier Type": "External ID",
}
PARAMS_BY_NAME: dict = {
    "Technique Identifier": ATTACK_PATTERN_NAME,
    "Identifier Type": "Name",
}
PARAMS_NOT_FOUND: dict = {
    "Technique Identifier": "attack-pattern--does-not-exist",
    "Identifier Type": "ID",
}
PARAMS_MULTI: dict = {
    # comma-separated: one hit + one miss
    "Technique Identifier": f"{ATTACK_PATTERN_ID}, attack-pattern--does-not-exist",
    "Identifier Type": "ID",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@set_metadata(parameters=PARAMS_BY_ID, integration_config=CONFIG)
def test_get_techniques_details_by_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Action succeeds and returns JSON results for a valid attack-pattern ID."""
    GetTechniquesDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert "Successfully retrieved" in result.output_message
    assert result.json_output is not None


@set_metadata(parameters=PARAMS_BY_EXTERNAL_ID, integration_config=CONFIG)
def test_get_techniques_details_by_external_id_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Action succeeds when queried by External ID (e.g. T1566.001)."""
    GetTechniquesDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_BY_NAME, integration_config=CONFIG)
def test_get_techniques_details_by_name_success(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Action succeeds when queried by technique name."""
    GetTechniquesDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True


@set_metadata(parameters=PARAMS_NOT_FOUND, integration_config=CONFIG)
def test_get_techniques_details_not_found(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """result_value is False and output says 'No techniques were found' when no match."""
    GetTechniquesDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is False
    assert "No techniques were found" in result.output_message


@set_metadata(parameters=PARAMS_MULTI, integration_config=CONFIG)
def test_get_techniques_details_partial_match(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Partial match: one ID found, one not — result_value True, both messages present."""
    GetTechniquesDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.COMPLETED
    assert result.result_value is True
    assert "Successfully retrieved" in result.output_message
    assert "wasn't able to find" in result.output_message


@set_metadata(parameters=PARAMS_BY_ID, integration_config=CONFIG)
def test_get_techniques_details_api_error(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
    mitre_product,
) -> None:
    """Unhandled HTTP error is caught; action returns FAILED with an error message."""
    with mitre_product.fail_requests():
        GetTechniquesDetails.main()

    result = action_output.results
    assert result.execution_state == ExecutionState.FAILED
    assert 'Error executing action "Get Technique Details"' in result.output_message

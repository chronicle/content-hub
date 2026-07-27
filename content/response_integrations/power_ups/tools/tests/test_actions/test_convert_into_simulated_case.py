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

from typing import TYPE_CHECKING

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from ...actions import ConvertIntoSimulatedCase
from ..common import (
    CONVERT_INTO_SIMULATED_CASE_ALERT_DETAILS_KEY,
    CONVERT_INTO_SIMULATED_CASE_CONTEXT,
    CONVERT_INTO_SIMULATED_CASE_EXPECTED_DATA_KEY,
)
from ..core.product import Tools
from ..core.session import ToolsSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


OUTPUT_MESSAGE: str = "Action result:  Pushed to Simulated "
IMPORT_CUSTOM_CASE: str = "importCustomCase"


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={
        "Push to Simulated Cases": True,
        "Save JSON as Case Wall File": False,
        "Override Alert Name": "",
        "Full path name": "",
    },
    input_context=CONVERT_INTO_SIMULATED_CASE_CONTEXT,
)
def test_convert_into_simulated_case_success(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test ConvertIntoSimulatedCase action success."""
    tools.set_alerts_full_details(
        load_mock_data[CONVERT_INTO_SIMULATED_CASE_ALERT_DETAILS_KEY]
    )

    ConvertIntoSimulatedCase.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert OUTPUT_MESSAGE in action_output.results.output_message

    assert len(script_session.request_history) == 2
    import_request = script_session.request_history[-1]
    assert import_request.request.method.value == "POST"
    assert IMPORT_CUSTOM_CASE.lower() in import_request.request.url.path.lower()

    payload = import_request.request.kwargs.get("json") or {}
    expected_json = load_mock_data[CONVERT_INTO_SIMULATED_CASE_EXPECTED_DATA_KEY]

    assert payload == expected_json

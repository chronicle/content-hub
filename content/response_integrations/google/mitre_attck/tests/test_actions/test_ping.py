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
from mitre_attck.actions import Ping
from mitre_attck.tests.common import CONFIG
from mitre_attck.tests.core.session import MitreAttckSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE: str = "Connection Established"
FAILURE_OUTPUT_MESSAGE: str = "Unable to connect to MitreAttack"


@set_metadata(integration_config=CONFIG)
def test_ping_success(
    script_session: MitreAttckSession,
    action_output: MockActionOutput,
) -> None:
    """Ping succeeds when the remote endpoint returns valid STIX data."""
    Ping.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    # Exactly one GET to the attack data endpoint
    assert len(script_session.request_history) == 1


@set_metadata(integration_config=CONFIG)
def test_ping_api_error(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
    mitre_product,
) -> None:
    """Ping fails gracefully when the remote endpoint returns a 500."""
    with mitre_product.fail_requests():
        Ping.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value in (False, "false")
    assert FAILURE_OUTPUT_MESSAGE in action_output.results.output_message


@set_metadata(integration_config=CONFIG)
def test_ping_empty_response(
    _script_session: MitreAttckSession,
    action_output: MockActionOutput,
    mitre_product,
) -> None:
    """Ping returns failure when the endpoint returns an empty/falsy JSON body.

    ISSUE FINDER: manager.test_connectivity() returns False only when
    get_raw_attack_data() is falsy.  An empty dict ``{}`` is falsy in Python,
    so this path exercises the ``return False`` branch in test_connectivity().
    """
    mitre_product.set_attack_data({})

    Ping.main()

    # Empty data means get_raw_attack_data() returns {} which is falsy →
    # test_connectivity returns False → action sets EXECUTION_STATE_FAILED
    # ISSUE FINDER: The action sets status=COMPLETED then overrides only
    # result_value, but it actually sets EXECUTION_STATE_FAILED inside the if/else.
    # Behaviour confirmed by reading the source: status = EXECUTION_STATE_FAILED on
    # the else branch.
    assert action_output.results.result_value in (False, "false")

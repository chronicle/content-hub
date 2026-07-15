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

import json
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout

from ..core import action_init, api_client, constants, exceptions

if TYPE_CHECKING:
    from typing import Any, NoReturn


class GetBlueAgentAnalysis(Action):
    def __init__(self) -> None:
        super().__init__(constants.GET_BLUE_AGENT_ANALYSIS_SCRIPT_NAME)
        self.error_output_message: str = (
            f'Error executing action "{constants.GET_BLUE_AGENT_ANALYSIS_SCRIPT_NAME}"'
        )

    @result_value.setter
    def result_value(self, value: Any) -> None:
        self._result_value = value

    def _extract_action_parameters(self) -> None:
        self.params.threat_id = extract_action_param(
            self.soar_action,
            param_name="Threat ID",
            is_mandatory=True,
            print_value=True,
        )

    def _init_api_clients(self) -> api_client.WizApiClient:
        return action_init.create_api_client(self.soar_action)

    def _is_approaching_async_timeout(self) -> bool:
        """Determine whether the action approaches asynchronous timeout."""
        return is_approaching_action_timeout(
            self.soar_action.async_total_duration_deadline,
        )

    def _perform_action(self, _: Any) -> None:
        if self._is_approaching_async_timeout():
            self.logger.info(
                "Action is approaching async timeout, and will exit gracefully."
            )
            raise TimeoutError("Action ran into a timeout during execution.")

        try:
            analysis = self.api_client.get_threat_ai_analysis(
                issue_id=self.params.threat_id
            )
        except exceptions.IssueNotFoundError as e:
            raise exceptions.IssueNotFoundError(
                f"Threat with ID {self.params.threat_id} wasn't found in "
                f"{constants.INTEGRATION_NAME}."
            ) from e

        if analysis is None:
            self.logger.info("Blue Agent analysis is not available for this threat.")
            self.output_message = (
                "Blue Agent analysis is not available for threat"
                f" {self.params.threat_id}."
            )
            self.result_value = False
            self.execution_state = ExecutionState.COMPLETED
        elif analysis.status == "COMPLETED":
            self.logger.info("Analysis is COMPLETED. Finishing action.")
            self.json_results = analysis.to_json()
            self.output_message = (
                "Successfully returned Blue Agent analysis for threat"
                f" {self.params.threat_id} in Wiz."
            )
            self.result_value = True
            self.execution_state = ExecutionState.COMPLETED
        else:
            self.logger.info(
                f"Analysis status is {analysis.status}. Execution state set to"
                " IN_PROGRESS."
            )
            self.output_message = (
                "Waiting for Wiz Blue Agent analysis for threat"
                f" {self.params.threat_id}."
            )
            self.result_value = json.dumps({})
            self.execution_state = ExecutionState.IN_PROGRESS


def main() -> NoReturn:
    GetBlueAgentAnalysis().run()


if __name__ == "__main__":
    main()

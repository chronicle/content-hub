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

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.types import Entity
from TIPCommon.validation import ParameterValidator

from web_risk.core.WebRiskBaseAction import BaseAction
from web_risk.core.WebRiskConstants import (
    CONFIDENCE_LEVELS,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    PLATFORMS,
    SUBMIT_ENTITIES_SCRIPT_NAME,
)
from web_risk.core.WebRiskDatamodels import (
    AbuseType,
    Submission,
    ThreatJustification,
    Operation,
)

SUCCESS_MESSAGE = "Successfully submitted the following entities in Web Risk: {}\n"
FAILURE_MESSAGE = (
    "The action wasn’t able to submit the following entities in Web Risk: {}"
)
NONE_UPDATED_MESSAGE = "No information was found for the provided entities."
PENDING_MESSAGE = "Submitting in progress."
TIMEOUT_MESSAGE = (
    "action ran into a timeout during execution. Please increase the timeout value "
    "in the Google SecOps IDE."
)


class SubmitEntities(BaseAction):

    def __init__(self) -> None:
        super().__init__(SUBMIT_ENTITIES_SCRIPT_NAME)
        self.output_message = NONE_UPDATED_MESSAGE
        self._entity_types = [
            EntityTypesEnum.URL,
        ]
        self.failed_entities = []
        self.execution_state = ExecutionState.COMPLETED
        self.result_value = self._result_value = False
        self.json_results = {}
        self.async_context: dict[str, Operation] = {}

    def is_approaching_async_timeout(self) -> bool:
        """Determine whether action approaches asynchronous timeout."""
        return is_approaching_action_timeout(
            self.soar_action.async_total_duration_deadline,
            GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 + NUM_OF_MILLI_IN_SEC
        )

    def _extract_parameters(self) -> None:
        """Extract action parameters."""
        self.params.abuse_type = extract_action_param(
            self.soar_action,
            param_name="Abuse Type",
            print_value=True,
        )
        self.params.confidence_level = extract_action_param(
            self.soar_action,
            param_name="Confidence Level",
            print_value=True,
        )
        self.params.justification = extract_action_param(
            self.soar_action,
            param_name="Justification",
            print_value=True,
        )
        self.params.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            print_value=True,
        )
        self.params.region_code = extract_action_param(
            self.soar_action,
            param_name="Region Code",
            print_value=True,
        )
        self.params.platform = extract_action_param(
            self.soar_action,
            param_name="Platform",
            print_value=True,
        )
        self.params.skip_waiting = extract_action_param(
            self.soar_action,
            param_name="Skip Waiting",
            input_type=bool,
            print_value=True,
        )
        self.async_context = {
            e_: Operation.from_json(op_) for e_, op_ in
            json.loads(
                extract_action_param(
                    self.soar_action, param_name="additional_data", default_value="{}"
                )
            ).items()
        }

    def _validate_params(self) -> None:
        """Validate action parameters."""
        validator = ParameterValidator(self.soar_action)
        self.params.abuse_type = (
            None if self.params.abuse_type == "Select One" else
            AbuseType(
                validator.validate_ddl(
                    "Abuse Type",
                    value=self.params.abuse_type,
                    ddl_values=[a.value for a in AbuseType]
                )
            )
        )
        self.params.justification = (
            None if self.params.justification == "Select One" else
            ThreatJustification(
                validator.validate_ddl(
                    "Justification",
                    value=self.params.justification,
                    ddl_values=[j.value for j in ThreatJustification],
                )
            )
        )
        self.params.confidence_level = CONFIDENCE_LEVELS[
            validator.validate_ddl(
                "Confidence Level",
                value=self.params.confidence_level,
                ddl_values=list(CONFIDENCE_LEVELS.keys())
            )
        ]
        self.params.platform = PLATFORMS[
            validator.validate_ddl(
                "Platform",
                value=self.params.platform,
                ddl_values=list(PLATFORMS.keys())
            )
        ]
        self.params.region_code_list = validator.validate_csv(
            "Region Code",
            csv_string=self.params.region_code
        )

    def _finalize_action_on_success(self) -> None:
        """On successful enrichment, update the output message."""
        if not self.async_context:
            return

        is_not_finalized = (
            not self.params.skip_waiting and
            any(op.is_running for op in self.async_context.values())
        )
        if is_not_finalized:
            self.execution_state = ExecutionState.IN_PROGRESS
            self.output_message = PENDING_MESSAGE
            self._result_value = json.dumps({
                entity: op.to_json() for entity, op
                in self.async_context.items()
            })
            return

        self.result_value = True
        self.output_message = SUCCESS_MESSAGE.format(
            ",".join(e for e in self.async_context)
        )
        if self.failed_entities:
            self.output_message += FAILURE_MESSAGE.format(
                ",".join(e.original_identifier for e in self.failed_entities)
            )

    def _on_entity_failure(
            self,
            current_entity: Entity,
            e: Exception
    ) -> None:
        """On entity failure callback."""
        if isinstance(e, TimeoutError):
            raise e

        del self.json_results[current_entity.original_identifier]
        self.failed_entities.append(current_entity)

    def _submit_uri(self, entity: Entity) -> Operation:
        """Submit URI if that's first run."""
        return self.api_client.submit_uri(
            submission=Submission(
                submission_uri=entity.original_identifier,
                abuse_type=self.params.abuse_type,
                confidence_level=self.params.confidence_level,
                justification=self.params.justification,
                comment=self.params.comment,
                region_codes=self.params.region_code_list,
                platform=self.params.platform
            )
        )

    def _query_operation(self, operation: Operation) -> Operation:
        """Query operation and update its status."""
        return self.api_client.get_operation(
            operation_name=operation.name,
        )

    def _perform_action(self, entity: Entity) -> None:
        """Enrich entity."""
        if self.is_approaching_async_timeout():
            raise TimeoutError(TIMEOUT_MESSAGE)

        if self.is_first_run:
            operation_ = self._submit_uri(entity)
        else:
            operation_ = self._query_operation(
                self.async_context[entity.original_identifier]
            )

        self.async_context[entity.original_identifier] = operation_
        self.json_results[entity.original_identifier] = operation_.to_json()


def main() -> None:
    SubmitEntities().run()


if __name__ == "__main__":
    main()

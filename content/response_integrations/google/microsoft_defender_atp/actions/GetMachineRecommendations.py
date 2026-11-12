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

from dataclasses import dataclass
from typing import Any, cast, TYPE_CHECKING

from TIPCommon.base.action import EntityTypesEnum as EntityTypes
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import get_entity_original_identifier

from ..core.base_action import BaseAction
from ..core.constants import (
    GET_MACHINE_RECOMMENDATIONS_SCRIPT_NAME,
    INTEGRATION_IDENTIFIER,
    MAX_RECOMMENDATIONS,
    MIN_RECOMMENDATIONS,
)
from ..core.datamodels import Machine, Recommendation
from ..core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPError,
    MicrosoftDefenderATPForbiddenError,
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPValidationError,
)

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo

    from TIPCommon.types import SingleJson


SUPPORTED_ENTITY_TYPES: list[int] = [
    EntityTypes.ADDRESS.value,
    EntityTypes.HOST_NAME.value,
]


@dataclass(slots=True)
class ActionData:
    """Data class for holding action state"""
    completed: list[str]
    no_recommendations: list[str]
    not_found: list[str]
    failed: list[str]


class GetMachineRecommendations(BaseAction):
    def __init__(self) -> None:
        super().__init__(GET_MACHINE_RECOMMENDATIONS_SCRIPT_NAME)
        self.api_client: MicrosoftDefenderATPManager
        self.action_data: ActionData | None = None
        self.json_results: list[SingleJson] = []
        self.output_message: str = ""
        self.result_value: bool = False

    def _extract_action_parameters(self) -> None:
        self.params.max_recommendations_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Recommendations To Return",
            print_value=True,
            input_type=int,
            default_value=100,
            is_mandatory=True,
        )

    def _validate_params(self) -> None:
        if not (
            MIN_RECOMMENDATIONS
            <= self.params.max_recommendations_to_return
            <= MAX_RECOMMENDATIONS
        ):
            raise ValueError(
                "Invalid value provided for 'Max Recommendations To Return': "
                f"{self.params.max_recommendations_to_return}. The value has to be in "
                f"range from {MIN_RECOMMENDATIONS} to "
                f"{MAX_RECOMMENDATIONS}."
            )

    def _perform_action(self, _: Any) -> None:
        self.logger.info(
            "Max recommendations to return: "
            f"{self.params.max_recommendations_to_return}"
        )

        suitable_entities: list[DomainEntityInfo] = [
            entity
            for entity in self.soar_action.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        if not suitable_entities:
            self.output_message: str = "No suitable entities found."
            self.result_value: bool = True
            return

        self.action_data = ActionData(
            completed=[],
            no_recommendations=[],
            not_found=[],
            failed=[],
        )

        try:
            for entity in suitable_entities:
                self._process_entity(entity)

            self._finalize_operation(suitable_entities)

        except (
            MicrosoftDefenderATPValidationError,
            MicrosoftDefenderATPForbiddenError,
            MicrosoftDefenderATPError,
        ) as error:
            self.result_value: bool = False
            self.output_message: str = (
                f"Error executing action “{self.soar_action.action_info.identifier}”. "
                f"Reason: {error}"
            )
            self.logger.exception(error)

    def _process_entity(self, entity: DomainEntityInfo) -> None:
        """Process a single entity to retrieve its machine recommendations.

        Args:
            entity (DomainEntityInfo): The entity to process.
        """
        entity_identifier: str = get_entity_original_identifier(entity)
        self.logger.info(f"Started processing entity: {entity_identifier}")

        try:
            machine, recommendations = self._get_machine_and_recommendations(
                entity,
                entity_identifier,
            )

            if machine:
                if recommendations:
                    self.json_results.append(
                        {
                            "Entity": entity_identifier,
                            "EntityResult": [rec.to_json() for rec in recommendations],
                        }
                    )
                    self.action_data.completed.append(entity_identifier)
                else:
                    self.action_data.no_recommendations.append(entity_identifier)
                    self.logger.info(
                        "No recommendations were found for the provided "
                        f"endpoints in {INTEGRATION_IDENTIFIER}: {machine.id}"
                    )
            else:
                self.action_data.not_found.append(entity_identifier)
                self.logger.info(f"Machine not found for entity {entity_identifier}")

            self.logger.info(f"Finished processing entity: {entity_identifier}")

        except MicrosoftDefenderATPError as e:
            self.action_data.failed.append(entity_identifier)
            self.logger.error(f"An error occurred on entity {entity_identifier}: {e}")

    def _get_machine_and_recommendations(
        self,
        entity: DomainEntityInfo,
        entity_identifier: str,
    ) -> tuple[Machine | None, list[Recommendation]]:
        """Retrieve the machine and its recommendations for a given entity.

        Args:
            entity (DomainEntityInfo): The entity to look up.
            entity_identifier (str): The original identifier of the entity.

        Returns:
            tuple[Machine | None, list[Recommendation]]: A tuple containing the Machine
            object (if found) and a list of Recommendation objects.
        """
        machines: list[Machine] = []
        if entity.entity_type == EntityTypes.HOST_NAME.value:
            machines = (
                self.api_client.get_machines_by_name(cast(str, entity_identifier)) or []
            )
        else:
            machines = self.api_client.get_machines(ip=entity_identifier) or []

        if not machines:
            return None, []

        machines: list[Machine] = sorted(machines, key=lambda m: m.last_seen_unix)
        machine: Machine = machines[-1]
        self.logger.info(f"Found machine {machine.id} for entity {entity_identifier}")

        recommendations: list[Recommendation] = (
            self.api_client.get_machine_recommendations(
                machine.id,
                limit=self.params.max_recommendations_to_return,
            )
        )

        return machine, recommendations

    def _finalize_operation(self, suitable_entities: list[DomainEntityInfo]) -> None:
        """Finalize the action and construct the output message and JSON results.

        Args:
            suitable_entities (list[DomainEntityInfo]): The list of entities that were
            processed.
        """
        if self.json_results:
            self.soar_action.result.add_result_json(self.json_results)

        output_messages: list[str] = []
        if self.action_data.completed:
            output_messages.append(
                "Successfully returned recommendations for the following "
                f"endpoints in {INTEGRATION_IDENTIFIER}: "
                f"{', '.join(self.action_data.completed)}."
            )

        entities_no_recommendations: list[str] = (
            self.action_data.no_recommendations + self.action_data.not_found
        )
        if entities_no_recommendations:
            if self.action_data.completed:
                output_messages.append(
                    "No recommendations were found for the following "
                    f"endpoints in {INTEGRATION_IDENTIFIER}: "
                    f"{', '.join(entities_no_recommendations)}."
                )

        if self.action_data.failed:
            if len(self.action_data.failed) == len(suitable_entities):
                self.result_value: bool = False
                self.output_message: str = (
                    f"Error executing action "
                    f"“{self.soar_action.action_info.identifier}”. "
                    f"Reason: Failed to process all entities."
                )
                return

            output_messages.append(
                "An error occurred on the following entities: "
                f"{', '.join(self.action_data.failed)}"
            )

        if output_messages:
            self.output_message: str = "\n".join(output_messages)
            self.result_value: bool = True
        elif not self.action_data.failed:
            self.output_message: str = (
                "No recommendations were found for the provided endpoints in "
                f"{INTEGRATION_IDENTIFIER}."
            )
            self.result_value: bool = True


def main() -> None:
    action = GetMachineRecommendations()
    action.run()


if __name__ == "__main__":
    main()

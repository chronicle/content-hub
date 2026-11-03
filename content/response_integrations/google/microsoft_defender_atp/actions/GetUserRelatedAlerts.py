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
from typing import Any

from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import get_entity_original_identifier

from ..core.base_action import BaseAction
from ..core.constants import (
    DEFAULT_MAX_ALERTS_TO_RETURN,
    GET_USER_RELATED_ALERTS_SCRIPT_NAME,
    MIN_ALERTS_LIMITS_TO_RETURN,
)
from ..core.datamodels import Alert
from ..core.exceptions import MicrosoftDefenderATPError


SUPPORTED_ENTITY_TYPES: list[str] = [EntityTypesEnum.USER.value]


@dataclass(slots=True)
class ActionData:
    """Data class for holding action state"""
    completed: list[str]
    failed: list[str]
    not_found: list[str]


class GetUserRelatedAlerts(BaseAction):
    def __init__(self) -> None:
        super().__init__(GET_USER_RELATED_ALERTS_SCRIPT_NAME)
        self.action_data: ActionData | None = None
        self.errors: list[str] = []
        self.json_results: list[dict] = []
        self.output_message: str = ""
        self.result_value: bool = True

    def _extract_action_parameters(self) -> None:
        self.params.max_alerts_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Alerts To Return",
            input_type=int,
            default_value=DEFAULT_MAX_ALERTS_TO_RETURN,
            print_value=True,
        )

    def _validate_params(self) -> None:
        if not (
            MIN_ALERTS_LIMITS_TO_RETURN
            <= self.params.max_alerts_to_return
            <= DEFAULT_MAX_ALERTS_TO_RETURN
        ):
            raise MicrosoftDefenderATPError(
                "Invalid value provided for 'Max Alerts To Return' parameter. "
                "Value should be between 1 and 100."
            )

    def _perform_action(self, _: Any) -> None:
        suitable_entities: list[EntityTypesEnum.USER] = [
            entity
            for entity in self.soar_action.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        if not suitable_entities:
            self.output_message: str = "No suitable entities found."
            self.result_value: bool = False
            return

        self.action_data: ActionData = ActionData(completed=[], failed=[], not_found=[])

        for entity in suitable_entities:
            self._process_entity(entity)

        self._finish_operation()

    def _process_entity(self, entity: Any) -> None:
        """Process a single entity to retrieve its alerts.

        Args:
            entity (Any): The entity to process.
        """
        entity_identifier: str = get_entity_original_identifier(entity)
        self.logger.info(f"Started processing entity: {entity_identifier}")

        try:
            username: EntityTypesEnum.USER = entity_identifier.split("@")[0]
            self.logger.info(f"Querying alerts for username: {username}")
            alerts: list[Alert] = self.api_client.get_user_related_alerts(
                user_id=username,
                limit=self.params.max_alerts_to_return,
            )

            if alerts:
                self.json_results.append(
                    {
                        "Entity": entity_identifier,
                        "EntityResult": [alert.to_json() for alert in alerts],
                    }
                )
                self.action_data.completed.append(entity_identifier)
            else:
                self.action_data.not_found.append(entity_identifier)

            self.logger.info(f"Finished processing entity {entity_identifier}")

        except MicrosoftDefenderATPError as e:
            self.action_data.failed.append(entity_identifier)
            self.errors.append(f"Failed to get alerts for {entity_identifier}: {e}")
            self.logger.error(f"An error occurred on entity {entity_identifier}")
            self.logger.exception(e)

    def _finish_operation(self) -> None:
        """Finish the operation and add the results to the action result."""
        if self.json_results:
            self.soar_action.result.add_result_json(self.json_results)

        if not self.action_data:
            self.output_message: str = "No alerts were found."
            return

        completed: list[str] = self.action_data.completed
        failed: list[str] = self.action_data.failed
        not_found: list[str] = self.action_data.not_found

        if not completed and not failed:
            self.output_message: str = (
                "No alerts were related to the provided users in Microsoft "
                "Defender for Endpoint."
            )
            return

        messages: list[str] = [
            self._format_completed_message(completed),
            self._format_not_found_message(not_found),
            self._format_failed_message(failed),
        ]

        if self.errors:
            messages.extend(self.errors)

        self.output_message: str = "\n".join(filter(None, messages)).strip()

    def _format_completed_message(self, completed: list[str]) -> str | None:
        """Formats a message for successfully processed entities.

        Args:
            completed (list[str]): A list of entity identifiers that were completed.

        Returns:
            str | None: A formatted string message listing the completed entities.
            Returns None if the 'completed' list is empty.
        """
        if not completed:
            return None

        return (
            "Successfully returned alerts related to the following users in "
            f"Microsoft Defender for Endpoint: {', '.join(completed)}."
        )

    def _format_not_found_message(self, not_found: list[str]) -> str | None:
        """Formats a message for entities that were not found.

        Args:
            not_found(list[str]): A list of entity identifiers that were not found.

        Returns:
            str | None: A formatted string message listing the not found entities.
            Returns None if the 'not_found' list is empty.
        """
        if not not_found:
            return None

        return (
            "No alerts were related to the following users in Microsoft "
            f"Defender for Endpoint: {', '.join(not_found)}."
        )

    def _format_failed_message(self, failed: list[str]) -> str | None:
        """Formats a message for entities that failed to process.

        Args:
            failed(list[str]): A list of entity identifiers that failed to process.

        Returns:
            str | None: A formatted string message listing the failed entities.
            Returns None if the 'failed' list is empty.
        """
        if not failed:
            return None

        return (
            "No alerts were related to the provided users in "
            "Microsoft Defender for Endpoint."
        )


def main() -> None:
    GetUserRelatedAlerts().run()


if __name__ == "__main__":
    main()

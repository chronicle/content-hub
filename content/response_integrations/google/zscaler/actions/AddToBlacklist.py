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

from TIPCommon.base.action.data_models import EntityTypesEnum

from ..core.base_action import ZscalerBaseAction
from ..core.constants import ADD_TO_BLACKLIST_SCRIPT_NAME
from ..core.exceptions import ZscalerManagerError

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import Entity


URL_ENTITY_TYPES = {
    EntityTypesEnum.URL.value,
    EntityTypesEnum.HOST_NAME.value,
    EntityTypesEnum.DOMAIN.value,
}


class AddToBlacklistAction(ZscalerBaseAction):
    def __init__(self) -> None:
        super().__init__(ADD_TO_BLACKLIST_SCRIPT_NAME)
        self.successful_entities: list[str] = []
        self.failed_entities: list[str] = []
        self._items_to_process: set[str] = set()
        self.output_message: str = ""
        self.result_value: bool = False

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.iocs = self.soar_action.extract_action_param(
            "IOCs", print_value=True
        )

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        """Get which entity types does the action work on"""
        return [
            EntityTypesEnum.URL,
            EntityTypesEnum.HOST_NAME,
            EntityTypesEnum.DOMAIN,
            EntityTypesEnum.ADDRESS,
        ]

    def _perform_action(self, entity: Entity) -> None:
        """Perform the action."""
        entity_to_block = self._get_entity_to_block(entity)

        if not entity_to_block:
            return

        self._items_to_process.add(entity_to_block)
        self.successful_entities.append(entity.identifier)

    def _get_entity_to_block(self, entity: Entity) -> str | None:
        """Extract entity value to block."""
        if entity.entity_type in URL_ENTITY_TYPES:
            return self.api_client.validate_and_extract_url(entity.identifier.lower())

        if (
            entity.entity_type == EntityTypesEnum.ADDRESS.value
            and not entity.is_internal
        ):
            return entity.identifier

        return None

    def _finalize_action_on_success(self) -> None:
        """Perform finalize steps right before the action ends in success."""
        self._process_iocs_parameter()

        if self._items_to_process:
            if not self._execute_bulk_operation():
                return

        if not self._activate_changes():
            return

        self._construct_output_message()

    def _execute_bulk_operation(self) -> bool:
        """Execute bulk operation."""
        try:
            self.api_client.add_multiple_to_blacklist(list(self._items_to_process))
            return True
        except ZscalerManagerError as e:
            self.logger.error(f"Failed to add entities to blacklist: {str(e)}")
            self.output_message = f"Failed to add entities to blacklist.\n{str(e)}."
            self.result_value = False
            return False

    def _activate_changes(self) -> bool:
        """Activate changes."""
        try:
            self.api_client.activate_changes()
            return True
        except ZscalerManagerError as e:
            self.logger.error(f"Failed to activate changes: {str(e)}")
            self.output_message = f"Failed to activate changes: {str(e)}"
            self.result_value = False
            return False

    def _construct_output_message(self) -> None:
        """Construct output message."""
        if self.successful_entities:
            joined_successful = "\n".join(self.successful_entities)
            self.output_message = (
                "Added the following entities to the Urls blacklist successfully:\n"
                f"{joined_successful}"
            )
            self.result_value = True

        if self.failed_entities:
            joined_failed = "\n".join(self.failed_entities)
            if self.output_message:
                self.output_message += (
                    "\n\nErrors occurred, check log for more information"
                )
            else:
                self.output_message = (
                    f"Failed to add the following entities:\n{joined_failed}"
                )
                self.result_value = False

        if not self.successful_entities and not self.failed_entities:
            self.output_message = "No entities were added to the Urls blacklist"
            self.result_value = False


def main() -> None:
    AddToBlacklistAction().run()


if __name__ == "__main__":
    main()

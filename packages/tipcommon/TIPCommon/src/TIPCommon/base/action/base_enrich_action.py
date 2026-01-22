# Copyright 2025 Google LLC
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

from abc import abstractmethod
from typing import Any

from ...exceptions import EnrichActionError
from ...types import Entity
from .base_action import Action
from .data_models import EntityTypesEnum


class EnrichAction(Action):
    """Class that represents an entities enrichment action.

    This class inherits from the
    TIPCommon.base.actions.base_action::Action class

    Args:
        name (str): The action name

    Attributes:
        enrichment_data (dict): This attribute holds the enrichment data for the
            current entity in each of the entity iterations.
            At the end of each iteration the entity's additional_properties
            attribute is updated with self.enrichment_data, meaning that this
            value should be set each time with new value - not appending to it
            the data each time.
        entity_results (Any): These are the entity results that should appear
            in the JSON results under this specific object

    Abstract Methods:
        - _get_entity_types(): Get the type of entities the action runs on
        - _perform_enrich_action(): Perform the main enrichment logic on an
            entity

    Private Methods:
        - _perform_action(): Do not override this method! This method combines
            The other abstract methods with more OOtB enrichment logic and
            passes it to the parent class to use in start()

    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.enrichment_data: dict = {}
        self.entity_results: Any = None

    # ==================== Abstract Method ==================== #

    @abstractmethod
    def _get_entity_types(self) -> list[EntityTypesEnum]:
        """Set which entity types the action accepts"""
        raise NotImplementedError

    @abstractmethod
    def _perform_enrich_action(
        self,
        current_entity: Entity | None = None,
    ) -> None:
        """Perform the main enrichment logic"""
        raise NotImplementedError

    # ==================== Action Methods ==================== #

    def _perform_action(
        self,
        current_entity: Entity | None = None,
    ) -> None:
        """Combines the other abstract methods to compose the enrich action
        with its out-of-the-box behavior.

        On each entity it performs the next steps:
            1) Perform the main enrichment logic
            2) If the enrichment data attribute was set then
                set it on the current entity
            3) Set the is_enriched flag of the entity to True
            4) Add the entity to a list of entities that should be updated
                in the platform after the action ends
            5) if the entity results attribute was set the add to the
                JSON result the entity results under the entity's
                original identifier (as the key) so later on it could be
                adjusted in the _get_adjusted_json_results() method to the
                Entity / EntityResults  JSON format

        Note:
            Do not override this method!

        Args:
            current_entity: _description_. Defaults to None.

        """
        try:
            self._perform_enrich_action(current_entity)

            if self.enrichment_data:
                self.logger.info("Setting enrichment data and adding it to the entity\n")
                current_entity.additional_properties.update(self.enrichment_data)

            self.logger.info("Setting the enriched property of the entity to true\n")
            current_entity.is_enriched = True
            self.entities_to_update.append(current_entity)

            if self.entity_results:
                self.logger.info("Setting enrichment results in JSON results\n")
                self.json_results[current_entity.original_identifier] = self.entity_results

        except Exception as e:
            raise EnrichActionError from e

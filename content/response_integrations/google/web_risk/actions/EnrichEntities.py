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
from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.types import Entity

from ..core.WebRiskBaseAction import BaseAction
from ..core.WebRiskConstants import ENRICH_ENTITIES_SCRIPT_NAME

SUCCESS_MESSAGE = "Successfully enriched the following entities in Web Risk: {}\n"
FAILURE_MESSAGE = (
    "The action wasn’t able to enrich the following entities in Web Risk: {}"
)
NONE_UPDATED_MESSAGE = "No information was found for the provided entities."


class EnrichEntities(BaseAction):

    def __init__(self) -> None:
        super().__init__(ENRICH_ENTITIES_SCRIPT_NAME)
        self.output_message = NONE_UPDATED_MESSAGE
        self._entity_types = [
            EntityTypesEnum.URL
        ]
        self.failed_entities = []
        self.result_value = False
        self.json_results = {}

    def _finalize_action_on_success(self) -> None:
        """On successful enrichment, update the output message."""
        if not self.entities_to_update:
            return

        self.output_message = SUCCESS_MESSAGE.format(
            ",".join(e.original_identifier for e in self.entities_to_update)
        )
        if self.failed_entities:
            self.output_message += FAILURE_MESSAGE.format(
                ",".join(e.original_identifier for e in self.failed_entities)
            )

    def _on_entity_failure(
            self,
            current_entity: Entity,
            _: Exception
    ) -> None:
        """On entity failure callback."""
        del self.json_results[current_entity.original_identifier]
        self.failed_entities.append(current_entity)

    def _perform_action(self, entity: Entity) -> None:
        """Enrich entity."""
        threat_object = self.api_client.search_uri(entity.original_identifier)
        if threat_object is None:
            self.failed_entities.append(entity)
            return

        threat_types = [
            tte.value
            for tte in threat_object.threat_types
        ]
        if threat_types:
            entity.additional_properties.update({
                "WebRisk_threatTypes": ",".join(threat_types)
            })

        entity.is_enriched = True
        self.entities_to_update.append(entity)

        self.result_value = True
        self.json_results[entity.original_identifier] = threat_object.to_json()


def main() -> None:
    EnrichEntities().run()


if __name__ == "__main__":
    main()

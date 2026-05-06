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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


def get_alert_entities(siemplify):
    return [entity for alert in siemplify.case.alerts for entity in alert.entities]


@output_handler
def main():
    siemplify = SiemplifyAction()

    entity_type = siemplify.parameters.get("Entity Type")
    delimiter = siemplify.parameters.get("Entity Delimiter")
    enrichment_field = siemplify.parameters.get("Enrichment Field")
    enrichment_value = siemplify.parameters.get("Enrichment Value")

    target_entities = list(
        filter(
            None,
            [
                x.strip()
                for x in siemplify.parameters.get("List of Entities", "").split(
                    delimiter,
                )
            ],
        ),
    )

    entities = []
    alert_entities = get_alert_entities(siemplify)
    for target_entity in target_entities:
        for entity in alert_entities:
            if entity.identifier.upper() == target_entity.upper() and entity.entity_type == entity_type:
                entities.append(entity)
                break

    updated_entities = []
    for entity in entities:
        entity.additional_properties[enrichment_field] = enrichment_value
        updated_entities.append(entity)

    count_updated_entities = len(updated_entities)

    if count_updated_entities > 0:
        siemplify.update_entities(updated_entities)

    siemplify.end(
        f"{count_updated_entities} entities were successfully enriched",
        count_updated_entities,
        EXECUTION_STATE_COMPLETED,
    )


if __name__ == "__main__":
    main()

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

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()

    json_data = siemplify.parameters.get("Fields to enrich")
    fields_to_enrich = json.loads(json_data)

    updated_entities = []

    for entity in siemplify.target_entities:
        for field in fields_to_enrich:
            entity.additional_properties[field["entity_field_name"]] = field["entity_field_value"]
        updated_entities.append(entity)

    count_updated_entities = len(updated_entities)

    if count_updated_entities > 0:
        siemplify.update_entities(updated_entities)

    for updated_entity in updated_entities:
        siemplify.result.add_json(
            updated_entity.identifier,
            json.dumps(fields_to_enrich),
        )

    siemplify.end(
        f"{count_updated_entities} entities were successfully were enriched",
        count_updated_entities,
        EXECUTION_STATE_COMPLETED,
    )


if __name__ == "__main__":
    main()

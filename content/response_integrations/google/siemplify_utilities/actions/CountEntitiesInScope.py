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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction


ACTION_NAME = "Siemplify_Count Entities In Scope"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    # Parameters.
    entity_type = siemplify.parameters.get("Entity Type")

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == entity_type
    ]

    list_count = len(scope_entities)

    output_message = f"There are {list_count} entities from {entity_type} type."

    siemplify.end(output_message, list_count)


if __name__ == "__main__":
    main()

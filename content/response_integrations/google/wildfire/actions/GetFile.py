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

import base64
from typing import List

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.WildfireManager import WildfireManager

INTEGRATION_NAME = "Wildfire"
ACTION_NAME = "Get File"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ACTION_NAME}"

    file_hash = extract_action_param(
        siemplify,
        param_name="File Hash",
        is_mandatory=False,
        print_value=True,
    )

    wildfire_manager = WildfireManager.from_siemplify(siemplify)

    errors: List[str] = []
    enriched_entities = []
    status = EXECUTION_STATE_COMPLETED
    json_results = {}

    # Case 1: An explicit File Hash parameter is provided
    if file_hash:
        try:
            sample = wildfire_manager.get_sample(file_hash)
            b64_content = base64.b64encode(sample["content"]).decode("utf-8")
            siemplify.result.add_attachment(sample["filename"], b64_content)

            # If an entity in the case matches this hash, attach directly to the entity too
            for entity in siemplify.target_entities:
                if entity.entity_type == EntityTypes.FILEHASH and entity.identifier.lower() == file_hash.lower():
                    siemplify.result.add_entity_attachment(entity.identifier, sample["filename"], b64_content)
                    enriched_entities.append(entity)

            json_results = {
                "file_hash": file_hash,
                "filename": sample["filename"],
                "downloaded": True,
            }
            output_message = f"Successfully downloaded file sample for {file_hash} from Wildfire."
            siemplify.result.add_result_json(json_results)
            siemplify.end(output_message, True, status)
            return

        except Exception as e:
            siemplify.LOGGER.exception(f"Failed to download sample for hash {file_hash}")
            output_message = f"Error executing action '{ACTION_NAME}'. Reason: {e}"
            siemplify.end(output_message, False, EXECUTION_STATE_FAILED)
            return

    # Case 2: Process target FILEHASH entities
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH:
            if len(entity.identifier) in (32, 64):
                try:
                    sample = wildfire_manager.get_sample(entity.identifier)
                    siemplify.result.add_entity_attachment(
                        entity.identifier,
                        sample["filename"],
                        base64.b64encode(sample["content"]).decode("utf-8"),
                    )
                    enriched_entities.append(entity)
                except Exception as e:
                    siemplify.LOGGER.exception(f"Failed to download sample for entity {entity.identifier}")
                    errors.append(f"{entity.identifier}: {e}")

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = "Files were downloaded for the following entities:\n" + "\n".join(entities_names)
        if errors:
            output_message += "\nErrors:\n" + "\n".join(errors)
        result_value = True
    else:
        output_message = "No files were downloaded."
        if errors:
            output_message += "\nErrors:\n" + "\n".join(errors)
        result_value = False

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

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

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.WildfireManager import WildfireManager, WildfireManagerError


@output_handler
def main():
    siemplify = SiemplifyAction()

    errors = ""
    enriched_entities = []

    try:
        wildfire_manager = WildfireManager.from_siemplify(siemplify)
    except Exception as e:
        siemplify.LOGGER.exception("Failed to initialize Wildfire manager")
        siemplify.end(f"Error executing action 'Get Pcap'. Reason: {e}", False, EXECUTION_STATE_FAILED)
        return

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH and len(entity.identifier) in {32, 64}:
            try:
                pcap_file = wildfire_manager.get_pcap(entity.identifier)
                siemplify.result.add_entity_attachment(
                    entity.identifier,
                    pcap_file["filename"],
                    base64.b64encode(pcap_file["content"]).decode("utf-8"),
                )
                enriched_entities.append(entity)

            except WildfireManagerError as e:
                errors += f"{e}\n"

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = "Report was saved for the following entities:\n" + "\n".join(
            entities_names
        )
        output_message += errors

    else:
        output_message = "No reports were downloaded.\n"
        output_message += errors

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()

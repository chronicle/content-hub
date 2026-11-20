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
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.WildfireManager import WildfireManager, WildfireNotFoundError

INTEGRATION_NAME = "Wildfire"
INTEGRATION_DISPLAY_NAME = "Palo Alto Wildfire"
ACTION_NAME = "Get Pcap"


def _format_entity_results(
    enriched_entities: list[Any],
    not_found_entities: list[str],
    failed_entities: list[str],
    errors: list[str],
) -> tuple[str, bool, int]:
    if enriched_entities:
        entities_str = ", ".join(entity.identifier for entity in enriched_entities)
        msg = (
            f"Successfully downloaded PCAP files for the following entities using "
            f"{INTEGRATION_DISPLAY_NAME}: {entities_str}."
        )
        unsuccessful = not_found_entities + failed_entities
        if unsuccessful:
            msg += (
                f"\nAction wasn't able to download PCAP files for the following entities using "
                f"{INTEGRATION_DISPLAY_NAME}: {', '.join(unsuccessful)}."
            )
        if errors:
            msg += "\nErrors:\n" + "\n".join(errors)
        return msg, True, EXECUTION_STATE_COMPLETED

    if errors:
        reasons = "; ".join(errors)
        return f'Error executing action "{ACTION_NAME}". Reason: {reasons}', False, EXECUTION_STATE_FAILED

    msg = f"No PCAP files were downloaded using {INTEGRATION_DISPLAY_NAME}."
    if not_found_entities:
        msg += (
            f"\nAction wasn't able to download PCAP files for the following entities using "
            f"{INTEGRATION_DISPLAY_NAME}: {', '.join(not_found_entities)}."
        )
    return msg, False, EXECUTION_STATE_COMPLETED


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ACTION_NAME}"

    try:
        wildfire_manager = WildfireManager.from_siemplify(siemplify)
    except Exception as e:
        siemplify.LOGGER.exception("Failed to initialize Wildfire manager")
        siemplify.end(f'Error executing action "{ACTION_NAME}". Reason: {e}', False, EXECUTION_STATE_FAILED)
        return

    enriched_entities: list[Any] = []
    not_found_entities: list[str] = []
    failed_entities: list[str] = []
    errors: list[str] = []

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
            except WildfireNotFoundError:
                siemplify.LOGGER.info(f"PCAP not found for entity {entity.identifier}")
                not_found_entities.append(entity.identifier)
            except Exception as e:
                siemplify.LOGGER.exception(f"Failed to download PCAP for entity {entity.identifier}")
                failed_entities.append(entity.identifier)
                errors.append(f"{entity.identifier}: {e}")

    msg, is_success, status = _format_entity_results(enriched_entities, not_found_entities, failed_entities, errors)
    siemplify.end(msg, is_success, status)


if __name__ == "__main__":
    main()

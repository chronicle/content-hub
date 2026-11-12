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
from soar_sdk.SiemplifyUtils import add_prefix_to_dict, dict_to_flat, flat_dict_to_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.WildfireManager import WildfireManager

INTEGRATION_NAME = "Wildfire"
ACTION_NAME = "Get Report"


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

    # Case 1: Explicit File Hash provided
    if file_hash:
        try:
            report = wildfire_manager.get_report(file_hash)
            siemplify.result.add_result_json(report)

            # Try to fetch and attach PDF report
            try:
                pdf_report = wildfire_manager.get_pdf_report(file_hash)
                siemplify.result.add_attachment(
                    pdf_report["filename"],
                    base64.b64encode(pdf_report["content"]).decode("utf-8"),
                )
            except Exception as pdf_err:
                siemplify.LOGGER.warn(f"Could not retrieve PDF report for {file_hash}: {pdf_err}")

            # Check if any case entity matches this hash to enrich it
            for entity in siemplify.target_entities:
                if entity.entity_type == EntityTypes.FILEHASH and entity.identifier.lower() == file_hash.lower():
                    file_info = dict(report.get("file_info") or {})
                    if file_info.get("malware") == "yes":
                        entity.is_suspicious = True
                        siemplify.add_entity_insight(entity, "File was found malicious by WildFire", triggered_by="WildFire")
                    file_info = add_prefix_to_dict(file_info, "Wildfire")
                    entity.additional_properties.update(file_info)
                    enriched_entities.append(entity)

            if enriched_entities:
                siemplify.update_entities(enriched_entities)

            output_message = f"Successfully downloaded report for {file_hash} from Wildfire."
            siemplify.end(output_message, True, status)
            return

        except Exception as e:
            siemplify.LOGGER.exception(f"Failed to download report for hash {file_hash}")
            output_message = f"Error executing action '{ACTION_NAME}'. Reason: {e}"
            siemplify.end(output_message, False, EXECUTION_STATE_FAILED)
            return

    # Case 2: Process target FILEHASH entities
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH:
            if len(entity.identifier) in (32, 64):
                try:
                    report = wildfire_manager.get_report(entity.identifier)
                    file_info = dict(report.get("file_info") or {})

                    if file_info.get("malware") == "yes":
                        entity.is_suspicious = True
                        siemplify.add_entity_insight(entity, "File was found malicious by WildFire", triggered_by="WildFire")

                    file_info = add_prefix_to_dict(file_info, "Wildfire")
                    entity.additional_properties.update(file_info)

                    # Attach table if task_info exists
                    if report.get("task_info"):
                        flat_reports = dict_to_flat(report["task_info"])
                        csv_output = flat_dict_to_csv(flat_reports)
                        siemplify.result.add_entity_table(entity.identifier, csv_output)

                    # Attach PDF
                    try:
                        pdf_report = wildfire_manager.get_pdf_report(entity.identifier)
                        siemplify.result.add_entity_attachment(
                            entity.identifier,
                            pdf_report["filename"],
                            base64.b64encode(pdf_report["content"]).decode("utf-8"),
                        )
                    except Exception as pdf_err:
                        siemplify.LOGGER.warn(f"Could not retrieve PDF report for {entity.identifier}: {pdf_err}")

                    enriched_entities.append(entity)

                except Exception as e:
                    siemplify.LOGGER.exception(f"Failed to get report for {entity.identifier}")
                    errors.append(f"{entity.identifier}: {e}")

    if enriched_entities:
        siemplify.update_entities(enriched_entities)
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = "Report was saved for the following entities:\n" + "\n".join(entities_names)
        if errors:
            output_message += "\nErrors:\n" + "\n".join(errors)
        result_value = True
    else:
        output_message = "No reports were downloaded."
        if errors:
            output_message += "\nErrors:\n" + "\n".join(errors)
        result_value = False

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

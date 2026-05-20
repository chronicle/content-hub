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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv, add_prefix_to_dict
from ..core.WildfireManager import WildfireManager
import base64


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Wildfire")
    api_key = conf["Api Key"]

    errors = ""
    enriched_entities = []

    # Connect to Wildfire
    wildfire_manager = WildfireManager(api_key)

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH:
            if len(entity.identifier) == 32 or len(entity.identifier) == 64:
                try:
                    # Hash is md5 ot sha256
                    report = wildfire_manager.get_report(entity.identifier)

                    # Enrich entity with file info
                    file_info = dict(report["file_info"])

                    # If entity is malware - mark entity as suspicious
                    if file_info["malware"] == "yes":
                        entity.is_suspicious = True
                        insight_msg = "File was found malicious by WildFire"
                        siemplify.add_entity_insight(
                            entity, insight_msg, triggered_by="WildFire"
                        )

                    file_info = add_prefix_to_dict(file_info, "Wildfire")
                    entity.additional_properties.update((dict(file_info)))

                    # Attach Reports as csv
                    flat_reports = dict_to_flat(report["task_info"])
                    csv_output = flat_dict_to_csv(flat_reports)
                    siemplify.result.add_entity_table(entity.identifier, csv_output)

                    # Get PDF report and attach it to results
                    pdf_report = wildfire_manager.get_pdf_report(entity.identifier)

                    siemplify.result.add_entity_attachment(
                        entity.identifier,
                        pdf_report["filename"],
                        base64.b64encode(pdf_report["content"]).decode("utf-8"),
                    )
                    enriched_entities.append(entity)

                except Exception as e:
                    errors += str(e) + "\n"

    if enriched_entities:
        siemplify.update_entities(enriched_entities)
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

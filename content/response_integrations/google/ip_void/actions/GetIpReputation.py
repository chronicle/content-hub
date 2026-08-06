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
from ..core.IPVoidManager import IPVoidManager
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyUtils import (
    construct_csv,
    create_entity_json_result_object,
    add_prefix_to_dict,
)

TRIGGER = "IPVoid"
SCRIPT_NAME = "IPVoid - Get IP Reputation"
INSIGHT_MSG = "Country: {0}"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("IPVoid")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]
    use_ssl = conf.get("Use SSL", "False").lower() == "true"

    ipvoid_manager = IPVoidManager(api_root, api_key, use_ssl=use_ssl)

    enriched_entities = []
    missing_entities = []
    failed_entities = []
    json_results = []
    output_message = ""
    action_state = EXECUTION_STATE_COMPLETED

    threshold = siemplify.parameters.get("Threshold", 0)

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            try:
                reputation = ipvoid_manager.get_ip_reputation(entity.identifier)

                if reputation:
                    blacklist_report = (
                        ipvoid_manager.create_blacklist_report_from_raw_data(reputation)
                    )

                    enrichment_data = reputation.get("information", {})
                    enrichment_data.update(reputation.get("anonymity", {}))
                    enrichment_data["detections"] = reputation.get(
                        "blacklists", {}
                    ).get("detections")
                    enrichment_data["detection_rate"] = reputation.get(
                        "blacklists", {}
                    ).get("detection_rate")
                    enrichment_data["engines_count"] = reputation.get(
                        "blacklists", {}
                    ).get("engines_count")

                    siemplify.result.add_entity_table(
                        entity.identifier, construct_csv(blacklist_report)
                    )

                    if enrichment_data.get("country_code"):
                        siemplify.add_entity_insight(
                            entity,
                            INSIGHT_MSG.format(enrichment_data.get("country_code")),
                            triggered_by=TRIGGER,
                        )

                    reputation["blacklists"]["engines"] = blacklist_report

                    enrichment_data = add_prefix_to_dict(enrichment_data, "IPVoid")
                    entity.additional_properties.update(enrichment_data)

                    json_results.append(
                        create_entity_json_result_object(entity.identifier, reputation)
                    )

                    if int(reputation.get("blacklists", {}).get("detections")) > int(
                        threshold
                    ):
                        entity.is_suspicious = True

                    entity.is_enriched = True
                    enriched_entities.append(entity)

                else:
                    missing_entities.append(entity)

            except Exception as e:
                failed_entities.append(entity)
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message += (
            "IPVoid: Fetched reputation for the following entities:\n{}\n".format(
                "\n".join(entities_names)
            )
        )

        siemplify.update_entities(enriched_entities)

    if failed_entities:
        output_message += "An error occurred on the following entities:\n{}\n".format(
            "\n".join([entity.identifier for entity in failed_entities])
        )
        action_state = EXECUTION_STATE_FAILED

    if missing_entities:
        output_message += "No reputation found for the following entities:\n{}".format(
            "\n".join([entity.identifier for entity in missing_entities])
        )

    if not missing_entities and not failed_entities and not enriched_entities:
        output_message = "IPVoid: No entities were enriched."

    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, "true", action_state)


if __name__ == "__main__":
    main()

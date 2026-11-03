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
from soar_sdk.SiemplifyUtils import (
    output_handler,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, construct_csv, extract_action_param
from threat_q.core.ThreatQManager import ThreatQManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from threat_q.core.constants import STATUS_MAPPING

# =====================================
#             CONSTANTS               #
# =====================================
THREATQ_PREFIX = "TQ"

INTEGRATION_NAME = "ThreatQ"
SCRIPT_NAME = "ThreatQ - Enrich CVE"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    # Variables Definitions.
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ServerAddress",
        input_type=str,
    )

    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ClientId", input_type=str
    )

    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username", input_type=str
    )

    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password", input_type=str
    )

    score_threshold = extract_action_param(
        siemplify=siemplify,
        param_name="Score Threshold",
        input_type=int,
        print_value=True,
        is_mandatory=False,
    )

    show_sources = extract_action_param(
        siemplify=siemplify,
        param_name="Show Sources",
        input_type=bool,
        print_value=True,
        is_mandatory=False,
    )

    show_comments = extract_action_param(
        siemplify=siemplify,
        param_name="Show Comments",
        input_type=bool,
        print_value=True,
        is_mandatory=False,
    )

    show_attributes = extract_action_param(
        siemplify=siemplify,
        param_name="Show Attributes",
        input_type=bool,
        print_value=True,
        is_mandatory=False,
    )

    mark_whitelisted_entities_as_suspicious = extract_action_param(
        siemplify=siemplify,
        param_name="Mark Whitelisted Entities As Suspicious",
        input_type=bool,
        print_value=True,
    )

    # Threshold should be in range from 0 to 10
    score_threshold = min(max(score_threshold, 0), 10)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.CVE
    ]

    entities_to_update = []
    failed_entities = []
    json_results = {}
    try:
        threatq_manager = ThreatQManager(server_address, client_id, username, password)
        for entity in scope_entities:
            try:
                # Get reports for entity by it's identifier.
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                cve_obj = threatq_manager.get_cve_object(entity.identifier)
                if cve_obj is None:
                    siemplify.LOGGER.info(
                        f"No CVE details ware found for entity: {entity.identifier}"
                    )
                    failed_entities.append(entity)
                    continue

                if cve_obj.indicator_score > score_threshold and (
                    mark_whitelisted_entities_as_suspicious
                    or cve_obj.indicator_status_id != STATUS_MAPPING.get("Whitelisted")
                ):
                    entity.is_suspicious = True

                entity.is_enriched = True

                json_results[entity.identifier] = cve_obj.to_json()
                entity.additional_properties.update(
                    add_prefix_to_dict_keys(cve_obj.to_flat_dict(), THREATQ_PREFIX)
                )
                entities_to_update.append(entity)

                # Case Wall
                flat_comments = cve_obj.comments_table()
                if flat_comments and show_comments:
                    siemplify.LOGGER.info(
                        f"Found {len(flat_comments)} comments for entity: {entity.identifier}"
                    )
                    siemplify.result.add_entity_table(
                        f"{entity.identifier} - Comments", construct_csv(flat_comments)
                    )

                flat_attributes = cve_obj.attributes_table()
                if flat_attributes and show_attributes:
                    siemplify.LOGGER.info(
                        f"Found {len(flat_attributes)} attributes for entity: {entity.identifier}"
                    )
                    siemplify.result.add_entity_table(
                        f"{entity.identifier} - Attributes",
                        construct_csv(flat_attributes),
                    )

                flat_sources = cve_obj.sources_table()
                if flat_sources and show_sources:
                    siemplify.LOGGER.info(
                        f"Found {len(flat_sources)} sources for entity: {entity.identifier}"
                    )
                    siemplify.result.add_entity_table(
                        f"{entity.identifier} - Sources", construct_csv(flat_sources)
                    )

                siemplify.LOGGER.info(
                    f"Finished processing entity: {entity.identifier}"
                )

            except Exception as e:
                output_message += f"Unable to enrich entity: {entity.identifier} \n"
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Failed processing entity:{entity.identifier}")
                siemplify.LOGGER.exception(e)

        if entities_to_update:
            siemplify.update_entities(entities_to_update)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message = f"Successfully enriched CVE:\n{', '.join([entity.identifier for entity in entities_to_update])}"
            result_value = "true"

        else:
            output_message = "CVEs were not enriched."
            result_value = "false"

        if failed_entities:
            output_message += "\nFailed to enrich the following entities:\n{0}".format(
                "\n".join([entity.identifier for entity in failed_entities])
            )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = "Some errors occurred. Please check log"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

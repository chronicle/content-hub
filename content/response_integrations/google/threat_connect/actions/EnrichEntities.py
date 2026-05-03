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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
    dict_to_flat,
    output_handler,
)
from TIPCommon import (
    convert_list_to_comma_string,
    extract_action_param,
    extract_configuration_param,
    string_to_multi_value,
)

from ..core.constants import ADDRESS, FILE, HOST, INTEGRATION_NAME, URL
from ..core.ThreatConnectManager import ThreatconnectAPI

ACTION_NAME = "ThreatConnect_EnrichEntities"


# Enrich target entity with threatConnect info and add web link with full details to entity
def enrich_entity(indicator_data, indicator_type, entity, siemplify):
    # Extract weblink
    try:
        link = indicator_data["general"][indicator_type]["webLink"]
        siemplify.result.add_entity_link(entity.identifier, link)
    except Exception as e:
        siemplify.LOGGER.error(
            f"Cannot extract link from entity data {entity.identifier}"
        )
        siemplify.LOGGER.exception(e)

    # Set risk level
    if indicator_data["general"][indicator_type].get("threatAssessRating", 0) > 1:
        entity.is_suspicious = True

    flat_report = dict_to_flat(indicator_data)
    flat_report = add_prefix_to_dict_keys(flat_report, "TC")
    entity.additional_properties.update(flat_report)
    entity.is_enriched = True
    return True


def add_insight(indicator_data, indicator_type, entity, siemplify):
    insight_msg = ""
    threat_asset_rating = (
        indicator_data.get("general", {})
        .get(indicator_type, {})
        .get("threatAssessRating")
    )
    confidence = (
        indicator_data.get("general", {}).get(indicator_type, {}).get("confidence")
    )
    description = (
        indicator_data.get("general", {}).get(indicator_type, {}).get("description")
    )
    tags_list = indicator_data.get("tags") or []
    tags = "| ".join(str(tag) for tag in tags_list)

    insight_msg += (
        f"Threat asset rating: {threat_asset_rating}. \n"
        if threat_asset_rating
        else "No threat asset rating. \n"
    )

    insight_msg += f"Confidence: {confidence}. \n" if confidence else "Confidence: 0 \n"

    insight_msg += (
        f"Description: {description}. \n" if description else "No description. \n"
    )

    insight_msg += f"Tags: {tags}. \n" if tags else "No tags. \n"

    siemplify.add_entity_insight(entity, insight_msg, triggered_by="ThreatConnect")


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")
    api_access_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiAccessId",
        is_mandatory=True,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiSecretKey",
        is_mandatory=True,
    )
    api_default_org = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiDefaultOrg",
        is_mandatory=True,
        print_value=True,
    )
    api_base_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ApiBaseUrl",
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters.
    owner_names = extract_action_param(
        siemplify, param_name="Owner Name", is_mandatory=False, print_value=True
    )

    enriched_entities = set()
    json_results = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    threat_connect = ThreatconnectAPI(
        api_access_id, api_secret_key, api_default_org, api_base_url
    )
    threat_connect.owner = api_default_org

    owner_names_list = string_to_multi_value(owner_names, only_unique=True)
    for entity in siemplify.target_entities:
        entity_original_identifier = entity.additional_properties.get(
            "OriginalIdentifier", entity.identifier.lower()
        )
        try:
            result_list = []
            for owner_name in owner_names_list:
                if entity.entity_type == EntityTypes.ADDRESS:
                    indicator_info = threat_connect.get_indicator_info(
                        ADDRESS, entity_original_identifier, owner_name
                    )
                    if indicator_info:
                        result_list.append(indicator_info)
                        json_results[entity.identifier] = result_list
                        enrich_entity(indicator_info, "address", entity, siemplify)
                        add_insight(indicator_info, "address", entity, siemplify)
                        enriched_entities.add(entity)

                if entity.entity_type == EntityTypes.FILEHASH:
                    indicator_info = threat_connect.get_indicator_info(
                        FILE, entity_original_identifier.upper(), owner_name
                    )
                    if indicator_info:
                        result_list.append(indicator_info)
                        json_results[entity.identifier] = result_list
                        enrich_entity(indicator_info, "file", entity, siemplify)
                        add_insight(indicator_info, "file", entity, siemplify)
                        enriched_entities.add(entity)

                if entity.entity_type == EntityTypes.URL:
                    indicator_info = threat_connect.get_indicator_info(
                        URL, entity_original_identifier, owner_name
                    )
                    if indicator_info:
                        result_list.append(indicator_info)
                        json_results[entity.identifier] = result_list
                        enrich_entity(indicator_info, "url", entity, siemplify)
                        add_insight(indicator_info, "url", entity, siemplify)
                        enriched_entities.add(entity)

                if entity.entity_type == EntityTypes.HOSTNAME:
                    indicator_info = threat_connect.get_indicator_info(
                        HOST, entity_original_identifier, owner_name
                    )
                    if indicator_info:
                        result_list.append(indicator_info)
                        json_results[entity.identifier] = result_list
                        enrich_entity(indicator_info, "host", entity, siemplify)
                        add_insight(indicator_info, "host", entity, siemplify)
                        enriched_entities.add(entity)

        except Exception as e:
            siemplify.LOGGER.error(f"Error enriching entity {entity.identifier}")
            siemplify.LOGGER.exception(e)

    if enriched_entities:
        enriched_entities_str = convert_list_to_comma_string(list(enriched_entities))
        output_message = (
            "Following entities were enriched by ThreatConnect. \n"
            f"'{enriched_entities_str}'"
        )
        result_value = "true"
        siemplify.update_entities(list(enriched_entities))
    else:
        output_message = "No entities were enriched."
        result_value = "false"

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

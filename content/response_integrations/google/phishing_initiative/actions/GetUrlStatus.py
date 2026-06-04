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

# Imports
from ..core.PhishingInitiativeManager import (
    PhishingInitiativeManager,
    NOT_SUBMIT_STATUS,
    PHISHING_STATUS,
)
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction

# Consts
URL = EntityTypes.URL


@output_handler
def main():
    siemplify = SiemplifyAction()
    # Configuration.
    conf = siemplify.get_configuration("PhishingInitiative")
    api_root = conf["Api Root"]
    api_token = conf["Api Token"]
    phishing_initiative = PhishingInitiativeManager(api_root, api_token)

    urls_to_enrich = []
    result_value = "false"
    urls_status = {}
    json_results = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == URL:
            res = phishing_initiative.get_url_info(entity.identifier.lower())
            if res:
                status = res[0]["tag_label"]
                json_results[entity.identifier] = res[0]
                urls_status.update({entity.identifier: status})
                if status != NOT_SUBMIT_STATUS:
                    entity.additional_properties["phishing_initiative_status"] = status
                    urls_to_enrich.append(entity)
                    entity.is_enriched = True
                if status == PHISHING_STATUS:
                    entity.is_suspicious = True
                    result_value = "true"

    if urls_status:
        output_message = "Following urls were found by Phishing-Initiative.\n\n"
        for identifier, status in list(urls_status.items()):
            output_message += f"{identifier}: Status: {status}\n"
        siemplify.update_entities(urls_to_enrich)
    else:
        output_message = "No entities were enriched."

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

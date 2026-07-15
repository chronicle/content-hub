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
from ..core.CertlyManager import CertlyManager
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Certly")
    api_token = conf["Api Token"]
    api_url = conf["Api Root"]
    certly = CertlyManager(api_token, api_url)

    urls_to_enrich = []
    result_value = "false"
    url_status = {}
    status = ""

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.URL:
            res = certly.get_url_status(entity.identifier)
        else:
            continue
        if res:
            status = res["data"][0]["status"]
            entity.additional_properties["Certly_Status"] = status
            entity.is_enriched = True
            urls_to_enrich.append(entity)

        url_status.update({entity.identifier: status})

        if status == "malicious":
            result_value = "true"
            entity.is_suspicious = True
            siemplify.add_entity_insight(entity, "Found as suspicious by Certly.")

    if urls_to_enrich:
        message = "Following Urls were enriched by Certly.\n"
        for identifier, status in list(url_status.items()):
            message += f"{identifier}: Status: {status}\n"
        output_message = message
        siemplify.update_entities(urls_to_enrich)
    else:
        output_message = "No entities were enriched."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

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
from soar_sdk.SiemplifyAction import *
from ..core.WebsenseManager import WebsenseAPIManager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Websense"


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Websense")
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    websense_manager = WebsenseAPIManager(
        conf["ApiRoot"], conf["GatewayUser"], conf["GatewayPassword"], verify_ssl
    )
    category = siemplify.parameters["CategoryName"]
    url = siemplify.parameters.get("Url")

    # Build using input parameter or siemplify entities
    if not url:
        urls = [
            entity.identifier
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.URL
        ]
    else:
        urls = [url]

    blocked_urls = []
    for url in urls:
        result = websense_manager.remove_url_form_category(url, category)
        if result:
            blocked_urls.append(url)

    if blocked_urls:
        result_value = "true"
        output_message = f"Urls:{blocked_urls} removed from category:{category}"
    else:
        output_message = "No Urls were unblocked"
        result_value = "False"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

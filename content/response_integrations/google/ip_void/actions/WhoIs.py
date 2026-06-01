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


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("IPVoid")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]
    use_ssl = conf.get("Use SSL", "False").lower() == "true"

    ipvoid_manager = IPVoidManager(api_root, api_key, use_ssl=use_ssl)

    found_entities = []

    for entity in siemplify.target_entities:
        if (
            entity.entity_type == EntityTypes.ADDRESS
            or entity.entity_type == EntityTypes.HOSTNAME
        ):
            html_report = ipvoid_manager.get_whois_html_report(entity.identifier)
            siemplify.result.add_entity_html_report(
                entity.identifier, "WhoIs Report", html_report
            )

            found_entities.append(entity)

    if found_entities:
        entities_names = [entity.identifier for entity in found_entities]

        output_message = (
            "IPVoid: Attached report for the following entities:\n"
            + "\n".join(entities_names)
        )

    else:
        output_message = "IPVoid: No reports were found."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()

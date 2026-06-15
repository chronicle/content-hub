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
from ..core.SEPManager import SEP14Manager
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "SEP"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "SEP - Block Hash"
    result_value = "false"
    output_message = ""
    errors = ""

    conf = siemplify.get_configuration("SEP")
    username = conf["Username"]
    password = conf["Password"]
    domain = conf["Domain"]
    url = conf["Api Root"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    black_list = siemplify.parameters["Black List Name"]
    sep_manager = SEP14Manager(url, username, password, domain, verify_ssl=verify_ssl)

    enriched_entities = []

    blacklisted_hashes = sep_manager.getBlackList(black_list)["data"]

    for entity in siemplify.target_entities:
        if (
            entity.entity_type == EntityTypes.FILEHASH
            and len(entity.identifier) == 32
            and not entity.identifier in blacklisted_hashes
        ):
            # Hash is MD5 and not already blacklisted
            enriched_entities.append(entity)
            blacklisted_hashes.append(entity.identifier)

    try:
        # Blacklist the hashes
        sep_manager.setBlackList("MD5", blacklisted_hashes)
    except Exception as e:
        # API call failed - no entities were enriched
        enriched_entities = []
        errors = f"Blocking failed: {str(e)}\n"
        siemplify.LOGGER.error(f"Blocking failed: {str(e)}\n")
        siemplify.LOGGER.exception(e)

    for entity in enriched_entities:
        entity.additional_properties.update({"SEP_IsBlocked": True})

    result_value = "true"

    if enriched_entities:
        entities_names = list(map(str, enriched_entities))

        output_message += (
            "The following hashes were blocked by Symantec Endpoint Protection:\n"
            + "\n".join(entities_names)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message += "No hashes were blocked.\n"
        output_message += errors

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()

# Copyright 2025 Google LLC
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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.types import SingleJson

from ..core.ToolsCommon import get_domain_from_string

# Consts:
INTEGRATION_NAME = "Tools"
SCRIPT_NAME = "Tools_ExtractURLDomain"


@output_handler
def main() -> None:
    """Execute the main function to extract URL domains."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    output_message = "No URLs processed"
    try:
        status = EXECUTION_STATE_COMPLETED
        result_value = 0
        failed_entities: list[SingleJson] = []
        successful_entities: list[SingleJson] = []
        json_result: dict[str, dict[str, str | dict[str, str]]] = {}
        out_message_list: list[str] = []

        urls = siemplify.parameters.get("URLs")
        extract_subdomain = (
            siemplify.extract_action_param(
                "Extract subdomain", print_value=True
            ).lower()
            == "true"
        )

        if urls:
            separator = siemplify.parameters.get("Separator")
            for url in urls.split(separator):
                try:
                    domain = get_domain_from_string(url.strip(), extract_subdomain)
                    if domain:
                        out_message_list.append(f"Domain extracted for param URL {url}")
                        json_result[url.strip()] = {
                            "domain": domain,
                            "source_entity_type": EntityTypes.URL,
                        }
                        result_value += 1
                    else:
                        out_message_list.append(
                            f"Invalid domain or suffix for URL {url}"
                        )
                        json_result[url.strip()] = {"Error": "Invalid domain or suffix"}

                except Exception as e:
                    out_message_list.append(
                        f"Failed extracting domain for param URL {url}"
                    )
                    json_result[url.strip()] = {"Error": f"Exception: {e}"}

        for entity in siemplify.target_entities:
            try:
                domain = get_domain_from_string(entity.identifier, extract_subdomain)
                if domain:
                    entity.additional_properties["siemplifytools_extracted_domain"] = (
                        domain
                    )
                    successful_entities.append(entity)
                    json_result[entity.identifier] = {
                        "domain": domain,
                        "source_entity_type": entity.entity_type,
                    }
                else:
                    failed_entities.append(entity)
                    json_result[entity.identifier] = {
                        "Error": "Invalid domain or suffix"
                    }
            except Exception as e:
                failed_entities.append(entity)
                json_result[entity.identifier] = {"Error": f"Exception: {e}"}

        if successful_entities:
            siemplify.update_entities(successful_entities)
            out_message_list.append(
                f"Domain extracted for {[x.identifier for x in successful_entities]}"
            )

        if failed_entities:
            out_message_list.append(
                "Failed extracting domain for "
                f"{[x.identifier for x in failed_entities]}"
            )

        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )
        if out_message_list:
            output_message = "\n".join(out_message_list)

        result_value += len(successful_entities)
    except Exception:
        siemplify.LOGGER.exception("General error performing action %s", SCRIPT_NAME)
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"
        raise

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

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
from ..core.ShodanManager import ShodanManager, ShodanIPNotFoundException
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_TIMEDOUT,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    unix_now,
    convert_unixtime_to_datetime,
)
from TIPCommon.transformation import flat_dict_to_csv, dict_to_flat
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_configuration_param, extract_action_param

INTEGRATION_NAME = "Shodan"
SCRIPT_NAME = "Get IP Info"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API key",
        is_mandatory=True,
        input_type=str,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    history = extract_action_param(
        siemplify,
        param_name="Return Historical Banners",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    minify = extract_action_param(
        siemplify,
        param_name="Set Minify",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    shodan = ShodanManager(api_key, verify_ssl=verify_ssl)

    errors = False
    status = EXECUTION_STATE_COMPLETED
    json_results = {}
    successful_entities = []
    missing_entities = []
    failed_entities = []
    result_value = "false"

    try:

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            if entity.entity_type == EntityTypes.ADDRESS:
                try:
                    siemplify.LOGGER.info(f"Processing entity {entity.identifier}")
                    ip_info = shodan.get_ip_info(
                        entity.identifier, history=history, minify=minify
                    )

                    if ip_info:
                        siemplify.LOGGER.info(
                            f"Found information for entity {entity.identifier}"
                        )
                        json_results[entity.identifier] = ip_info

                        # Add csv table
                        siemplify.LOGGER.info(
                            f"Adding CSV table for {entity.identifier}"
                        )
                        flat_report = dict_to_flat(ip_info)
                        csv_output = flat_dict_to_csv(flat_report)
                        siemplify.result.add_entity_table(entity.identifier, csv_output)

                        # enrich
                        if not minify:
                            domains_list = ip_info.get("data")[0].get("domains")
                        else:
                            domains_list = ip_info.get("domains")
                        domains = ",".join(domains_list)
                        entity.additional_properties.update(
                            {
                                "Shodan_Country": ip_info.get("country_name"),
                                "Shodan_Last_updated": ip_info.get("last_update"),
                                "Shodan_Domains": domains,
                            }
                        )
                        entity.is_enriched = True
                        successful_entities.append(entity)

                    else:
                        siemplify.LOGGER.info(
                            f"No information was found for entity {entity.identifier}"
                        )

                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )

                except ShodanIPNotFoundException:
                    # Entity not found
                    siemplify.LOGGER.error(
                        f"Entity {entity.identifier} was not found in Shodan."
                    )
                    missing_entities.append(entity)

                except Exception as e:
                    # An error occurred - skip entity and continue
                    siemplify.LOGGER.error(
                        f"An error occurred on entity: {entity.identifier}\n{e}."
                    )
                    siemplify.LOGGER.exception(e)
                    failed_entities.append(entity)

        if successful_entities:
            output_message = "The following IPs were submitted and analyzed in Shodan:\n   {}".format(
                "\n   ".join([entity.identifier for entity in successful_entities])
            )
            siemplify.update_entities(successful_entities)
            result_value = "true"

        else:
            output_message = "No entities were enriched."

        if missing_entities:
            output_message += (
                "\n\nThe following entities were not found in Shodan:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in missing_entities])
                )
            )

        if failed_entities:
            output_message += (
                "\n\nFailed enriching the following entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in failed_entities])
                )
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error occurred while running action {SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"An error occurred while running action. Error: {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

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
    convert_unixtime_to_datetime,
    flat_dict_to_csv,
    output_handler,
    unix_now,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.action_init import create_api_client
from ..core.constants import INTEGRATION_NAME, ENRICH_ENTITIES_ACTION_SCRIPT_NAME
from ..core.exceptions import XDRNotFoundException


SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ENRICH_ENTITIES_ACTION_SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    missing_entities = []
    json_results = {}
    failed_entities = []
    output_message = ""
    result_value = "true"

    try:
        xdr_manager = create_api_client(siemplify)

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                endpoint = None

                if entity.entity_type == EntityTypes.HOSTNAME:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching endpoint for hostname {entity.identifier}"
                        )
                        endpoint = xdr_manager.get_endpoint_by_hostname(
                            entity.identifier
                        )
                    except XDRNotFoundException as e:
                        # Endpoint was not found in Cortex XDR - skip entity
                        missing_entities.append(entity)
                        siemplify.LOGGER.info(str(e))
                        siemplify.LOGGER.info(f"Skipping entity {entity.identifier}")
                        continue

                if entity.entity_type == EntityTypes.ADDRESS:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching endpoint for address {entity.identifier}"
                        )
                        endpoint = xdr_manager.get_endpoint_by_ip(entity.identifier)
                    except XDRNotFoundException as e:
                        # Endpoint was not found in Cortex XDR - skip entity
                        missing_entities.append(entity)
                        siemplify.LOGGER.info(str(e))
                        siemplify.LOGGER.info(f"Skipping entity {entity.identifier}")
                        continue

                entity.additional_properties.update(
                    add_prefix_to_dict_keys(
                        endpoint.as_enrichment_data(), INTEGRATION_NAME
                    )
                )

                json_results[entity.identifier] = endpoint.raw_data
                siemplify.result.add_entity_table(
                    f"Entity {entity.identifier} details found",
                    flat_dict_to_csv(endpoint.as_csv()),
                )
                entity.is_enriched = True

                successful_entities.append(entity)
                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "Successfully enriched entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in successful_entities])
            )
            siemplify.update_entities(successful_entities)
        else:
            output_message += "No entities were enriched."

        if missing_entities:
            output_message += "\n\nAction was not able to find endpoints matching the following entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in missing_entities])
            )

        if failed_entities:
            output_message += (
                "\n\nFailed enriching the following entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in failed_entities])
                )
            )

    except Exception as e:
        siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Action didn't complete due to error: {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

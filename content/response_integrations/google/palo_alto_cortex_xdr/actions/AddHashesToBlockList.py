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
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from TIPCommon.extraction import extract_action_param

from ..core.action_init import create_api_client
from ..core.constants import ADD_HASHES_TO_BLOCK_LIST_ACTION_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import XDRAlreadyExistsException


SUPPORTED_ENTITIES = [EntityTypes.FILEHASH]
SUCCESSFUL = "success"
FAILED = "failed"
ALREADY_EXISTED = "already_existed"
UNSUPPORTED = "unsupported"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_NAME} - {ADD_HASHES_TO_BLOCK_LIST_ACTION_SCRIPT_NAME}"
    )
    siemplify.LOGGER.info("================= Main - Param Init =================")
    comment = extract_action_param(
        siemplify,
        param_name="Comment",
        default_value=None,
        input_type=str,
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    failed_entities = []
    duplicate_entities = []
    unsupported_hashes_entities = []
    output_messages = []
    result_value = False
    json_results = {SUCCESSFUL: [], FAILED: [], ALREADY_EXISTED: [], UNSUPPORTED: []}

    try:
        xdr_manager = create_api_client(siemplify)

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                if not xdr_manager.is_sha256(entity.identifier):
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is not a valid SHA256 hash. Skipping."
                    )
                    unsupported_hashes_entities.append(entity)
                    continue

                siemplify.LOGGER.info(f"Adding hash {entity.identifier} to Block List")
                xdr_manager.add_hash_to_block_list(entity.identifier, comment)

                successful_entities.append(entity)

            except XDRAlreadyExistsException as e:
                duplicate_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            output_messages.append(
                "Successfully added the following entities to the Block List:\n{}".format(
                    "\n".join([entity.identifier for entity in successful_entities])
                )
            )
            result_value = True
            json_results[SUCCESSFUL] = [
                entity.identifier for entity in successful_entities
            ]
        else:
            output_messages.append("No entities were added to Block List.")

        if failed_entities:
            output_messages.append(
                "Could not add the following entities to the Block List:\n{}".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )
            )
            json_results[FAILED] = [entity.identifier for entity in failed_entities]

        if duplicate_entities:
            output_messages.append(
                "The following entities already exist in the Block List:\n{}".format(
                    "\n".join([entity.identifier for entity in duplicate_entities])
                )
            )
            json_results[ALREADY_EXISTED] = [
                entity.identifier for entity in duplicate_entities
            ]

        if unsupported_hashes_entities and not (
            successful_entities or failed_entities or duplicate_entities
        ):
            output_messages.append("None of the provided hashes are supported.")
            json_results[UNSUPPORTED] = [
                entity.identifier for entity in unsupported_hashes_entities
            ]
        elif unsupported_hashes_entities:
            output_messages.append(
                "The following hashes are unsupported:\n{}".format(
                    "\n".join(
                        [entity.identifier for entity in unsupported_hashes_entities]
                    )
                )
            )
            json_results[UNSUPPORTED] = [
                entity.identifier for entity in unsupported_hashes_entities
            ]

        output_message = "\n".join(output_messages)

        if any(json_results.values()):
            siemplify.result.add_result_json(json_results)

    except Exception as e:
        siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to perform action {ADD_HASHES_TO_BLOCK_LIST_ACTION_SCRIPT_NAME}. "
            f"Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()

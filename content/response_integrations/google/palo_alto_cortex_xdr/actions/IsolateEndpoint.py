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
from datetime import datetime
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.types import SingleJson

from palo_alto_cortex_xdr.core.action_init import create_api_client
from palo_alto_cortex_xdr.core.constants import (
    ISOLATE_ENDPOINT_ACTION_SCRIPT_NAME,
    AGENT_ID_VALIDATION_REGEX,
)
from palo_alto_cortex_xdr.core.exceptions import XDRException, XDRNotFoundException
from palo_alto_cortex_xdr.core.XDRManager import XDRManager


SUPPORTED_ENTITIES: list[EntityTypes] = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ISOLATE_ENDPOINT_ACTION_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    agent_ids_str = siemplify.extract_action_param(
        param_name="Agent ID",
        is_mandatory=False,
        print_value=True,
        default_value="",
    )
    agent_ids: list[str] = string_to_multi_value(string_value=agent_ids_str)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    if not siemplify.target_entities and not agent_ids:
        output_message = "No entities or agent IDs were provided to isolate."
        siemplify.end(output_message, "true", EXECUTION_STATE_COMPLETED)

    status: str = EXECUTION_STATE_COMPLETED
    successful_entities: list[EntityTypes] = []
    missing_entities: list[EntityTypes] = []
    failed_entities: list[EntityTypes] = []
    output_message: str = ""
    result_value: str = "true"

    successful_agent_ids: list[str] = []
    failed_agent_ids: list[str] = []
    invalid_agent_ids: list[str] = []
    processed_endpoint_ids: set[str] = set()

    try:
        xdr_manager: XDRManager = create_api_client(siemplify)

        for entity in siemplify.target_entities:
            if is_approaching_action_timeout(siemplify.execution_deadline_unix_time_ms):
                deadline_time: datetime = convert_unixtime_to_datetime(
                    siemplify.execution_deadline_unix_time_ms
                )
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({deadline_time}) has passed"
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
                endpoint: SingleJson | None = None

                if entity.entity_type == EntityTypes.HOSTNAME:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching endpoint for hostname {entity.identifier}"
                        )
                        endpoint = xdr_manager.get_endpoint_by_hostname(
                            entity.identifier,
                        )
                    except XDRNotFoundException as e:
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
                        missing_entities.append(entity)
                        siemplify.LOGGER.info(str(e))
                        siemplify.LOGGER.info(f"Skipping entity {entity.identifier}")
                        continue

                if endpoint is not None:
                    processed_endpoint_ids.add(endpoint.endpoint_id)

                siemplify.LOGGER.info(
                    f"Initiating isolation of endpoint {entity.identifier}"
                )
                xdr_manager.isolate_endpoint(endpoint.endpoint_id)

                successful_entities.append(entity)
                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        for agent_id in agent_ids:
            if is_approaching_action_timeout(siemplify.execution_deadline_unix_time_ms):
                siemplify.LOGGER.error("Timed out during Agent ID processing.")
                status = EXECUTION_STATE_TIMEDOUT
                break

            result: str = process_single_agent(
                siemplify,
                xdr_manager,
                agent_id,
                processed_endpoint_ids,
            )

            if result == "success":
                successful_agent_ids.append(agent_id)
            elif result == "failed":
                failed_agent_ids.append(agent_id)
            elif result == "invalid":
                invalid_agent_ids.append(agent_id)

        all_successful: list[str] = [
            entity.identifier for entity in successful_entities
        ] + successful_agent_ids
        all_failed: list[str] = [
            entity.identifier for entity in failed_entities
        ] + failed_agent_ids

        if all_successful:
            endpoints_str = "\n   ".join(all_successful)
            output_message += (
                "Successfully initiated isolation of the following endpoints:\n"
                f"   {endpoints_str}"
            )
            if successful_entities:
                siemplify.update_entities(successful_entities)
        else:
            output_message += "No endpoints were isolated."

        if invalid_agent_ids:
            invalid_ids_str = "\n   ".join(invalid_agent_ids)
            output_message += (
                "\n\nThe following agent IDs have an invalid format and were "
                f"skipped:\n   {invalid_ids_str}"
            )

        if missing_entities:
            entities_str = "\n   ".join(
                [entity.identifier for entity in missing_entities]
            )
            output_message += (
                "\n\nAction was not able to find endpoints matching the "
                f"following entities:\n   {entities_str}"
            )

        if all_failed:
            failed_str: str = "\n   ".join(all_failed)
            output_message += (
                f"\n\nFailed to isolate the following endpoints:\n   {failed_str}"
            )

        if not all_successful:
            result_value = "false"

    except Exception as e:
        siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Action didn't complete due to error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


def process_single_agent(
    siemplify: SiemplifyAction,
    xdr_manager: XDRManager,
    agent_id: str,
    processed_endpoint_ids: set[str],
) -> str:
    """Processes a single agent ID for isolation.

    Args:
        siemplify (SiemplifyAction): The SiemplifyAction object.
        xdr_manager (XDRManager): The XDRManager object.
        agent_id (str): The agent ID to process.
        processed_endpoint_ids (set): A set of endpoint IDs that have already
            been processed.

    Returns:
        str: A status string: 'success', 'failed', 'invalid', or 'skipped'.
    """
    try:
        if not bool(AGENT_ID_VALIDATION_REGEX.fullmatch(agent_id)):
            siemplify.LOGGER.info(
                f"Agent ID {agent_id} has an invalid format. Skipping."
            )
            return "invalid"

        if agent_id in processed_endpoint_ids:
            siemplify.LOGGER.info(
                f"Agent ID {agent_id} was already processed via a "
                "target entity. Skipping."
            )
            return "skipped"

        siemplify.LOGGER.info(f"Initiating isolation for Agent ID: {agent_id}")
        xdr_manager.isolate_endpoint(agent_id)
        siemplify.LOGGER.info(
            f"Successfully initiated isolation for Agent ID: {agent_id}"
        )
        return "success"

    except XDRException as e:
        siemplify.LOGGER.error(f"An error occurred on Agent ID {agent_id}")
        siemplify.LOGGER.exception(e)
        return "failed"


if __name__ == "__main__":
    main()

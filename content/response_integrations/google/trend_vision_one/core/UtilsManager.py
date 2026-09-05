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

from typing import Any

import os

import json
import re

from .TrendVisionOneManager import TrendVisionOneManager
from .TrendVisionOneExceptions import (
    TrendVisionOneException,
    TrendVisionOneTimeoutException,
)

from .constants import (
    DEFAULT_TIMEOUT,
    ENRICHMENT_PREFIX,
    FAILED_STATUS,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    IN_BLOCKLIST_KEY,
    INTEGRATION_NAME,
    OBJECT_TYPE_DOMAIN,
    OBJECT_TYPE_FILE_SHA1,
    OBJECT_TYPE_FILE_SHA256,
    OBJECT_TYPE_IP,
    OBJECT_TYPE_SENDER_MAIL_ADDRESS,
    OBJECT_TYPE_URL,
    PARAM_DESCRIPTION,
    PARAM_DOMAINS,
    PARAM_EMAIL_ADDRESSES,
    PARAM_FILE_HASHES,
    PARAM_IPS,
    PARAM_URLS,
    PAYLOAD_CHUNK_SIZE,
    REJECTED_STATUS,
    SUCCESS_STATUS,
)
from . import datamodels
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    is_approaching_timeout,
    string_to_multi_value,
)




def get_entity_original_identifier(entity: Any) -> str:
    """
    Helper function for getting entity original identifier
    Args:
        entity: entity from which function will get original identifier

    Returns:
        original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def check_submit_files_in_system(files: list) -> list:
    """Return not accessible or not found files in filesystem.

    Args:
        files (list): list of files.

    Returns:
        list: list of not found files.
    """
    not_found_files = [
        file
        for file in files
        if not (os.path.exists(file) and os.access(file, os.R_OK))
    ]

    return not_found_files


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
    )


def process_agents(
    manager: TrendVisionOneManager,
    agent_uids: list[str],
) -> datamodels.AgentResult:
    """Process a list of agent UUIDs, searching for each agent and categorizing them as
    successful or failed.

    Args:
        manager (TrendVisionOneManager): An instance of the TrendVisionOneManager for
        interacting with the API.
        agent_uids (list[str]): A list of agent UUIDs to process.

    Returns:
        AgentResult: An object containing two lists: `successful_agents`
        (list of Endpoint objects) and `failed_agents` (list of agent UUIDs
        that could not be processed).
    """
    agent_result: datamodels.AgentResult = datamodels.AgentResult([], [])
    for agent_id in agent_uids:
        try:
            if (agent := manager.search_endpoint(agent_id=agent_id)) is not None:
                agent_result.successful_agents.append(agent)
            else:
                agent_result.failed_agents.append(agent_id)
                manager.siemplify.LOGGER.info(f"Agent UUID not found: {agent_id}")

        except TrendVisionOneException as e:
            agent_result.failed_agents.append(agent_id)
            manager.siemplify.LOGGER.error(f"An error occurred on agent: {agent_id}")
            manager.siemplify.LOGGER.exception(e)

    return agent_result


SUPPORTED_BLOCKLIST_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.URL,
    EntityTypes.USER,
    EntityTypes.FILEHASH,
]

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _extract_entity_object(entity: Any, siemplify: SiemplifyAction) -> tuple[str, str, str] | None:
    """Extracts suspicious object type and normalized value from a Chronicle entity.

    Returns:
        tuple of (object_type, normalized_value, original_identifier) or None if skipped.
    """
    original_identifier = get_entity_original_identifier(entity).strip()
    if not original_identifier:
        return None

    if entity.entity_type == EntityTypes.ADDRESS:
        return (OBJECT_TYPE_IP, original_identifier, original_identifier)

    if entity.entity_type == EntityTypes.HOSTNAME:
        return (OBJECT_TYPE_DOMAIN, original_identifier, original_identifier)

    if entity.entity_type == EntityTypes.URL:
        return (OBJECT_TYPE_URL, original_identifier, original_identifier)

    if entity.entity_type == EntityTypes.USER:
        if EMAIL_REGEX.match(original_identifier):
            return (OBJECT_TYPE_SENDER_MAIL_ADDRESS, original_identifier, original_identifier)
        siemplify.LOGGER.info(
            f"Skipping USER entity '{original_identifier}' because it does not match email pattern."
        )
        return None

    if entity.entity_type == EntityTypes.FILEHASH:
        hash_len = len(original_identifier)
        if hash_len == 40:
            return (OBJECT_TYPE_FILE_SHA1, original_identifier.lower(), original_identifier)
        if hash_len == 64:
            return (OBJECT_TYPE_FILE_SHA256, original_identifier.lower(), original_identifier)
        siemplify.LOGGER.info(
            f"Skipping FILEHASH entity '{original_identifier}' because only SHA1 (40 hex) and SHA256 (64 hex) are supported."
        )
        return None

    return None


def _extract_manual_parameter_objects(siemplify: SiemplifyAction) -> list[tuple[str, str, str]]:
    """Extracts and normalizes suspicious objects from manual action parameters.

    Returns:
        list of tuples (object_type, normalized_value, raw_value).
    """
    param_configs = [
        (PARAM_IPS, OBJECT_TYPE_IP),
        (PARAM_DOMAINS, OBJECT_TYPE_DOMAIN),
        (PARAM_URLS, OBJECT_TYPE_URL),
        (PARAM_FILE_HASHES, "hash"),
        (PARAM_EMAIL_ADDRESSES, OBJECT_TYPE_SENDER_MAIL_ADDRESS),
    ]
    extracted_objects: list[tuple[str, str, str]] = []

    for param_name, obj_type in param_configs:
        raw_val = extract_action_param(siemplify, param_name=param_name, is_mandatory=False)
        if not raw_val:
            continue
        items = string_to_multi_value(raw_val)
        for item in items:
            item_clean = item.strip()
            if not item_clean:
                continue

            if obj_type == "hash":
                hash_len = len(item_clean)
                if hash_len == 40:
                    extracted_objects.append((OBJECT_TYPE_FILE_SHA1, item_clean.lower(), item_clean))
                elif hash_len == 64:
                    extracted_objects.append((OBJECT_TYPE_FILE_SHA256, item_clean.lower(), item_clean))
                else:
                    siemplify.LOGGER.info(
                        f"Skipping manual hash '{item_clean}' because only SHA1 and SHA256 are supported."
                    )
            elif obj_type == OBJECT_TYPE_SENDER_MAIL_ADDRESS:
                if EMAIL_REGEX.match(item_clean):
                    extracted_objects.append((OBJECT_TYPE_SENDER_MAIL_ADDRESS, item_clean, item_clean))
                else:
                    siemplify.LOGGER.info(
                        f"Skipping manual email '{item_clean}' because it does not match email pattern."
                    )
            else:
                extracted_objects.append((obj_type, item_clean, item_clean))

    return extracted_objects


def build_blocklist_payloads(
    siemplify: SiemplifyAction,
    suitable_entities: list[Any],
    description: str | None = None,
    is_add: bool = True,
) -> tuple[list[dict], dict[str, str]]:
    """Builds suspicious object payloads and identifier-to-type mapping from entities and free text params."""
    payloads: list[dict] = []
    entity_map: dict[str, str] = {}
    seen_keys: set[tuple[str, str]] = set()

    def _add_payload(obj_type: str, val: str, entity_ident: str) -> None:
        key = (obj_type, val)
        if key in seen_keys:
            return
        seen_keys.add(key)
        item: dict[str, Any] = {obj_type: val}
        if is_add and description:
            item["description"] = description
        payloads.append(item)
        entity_map[entity_ident] = obj_type

    # 1. Process entities in scope
    for entity in suitable_entities:
        extracted = _extract_entity_object(entity, siemplify)
        if extracted:
            obj_type, val, entity_ident = extracted
            _add_payload(obj_type, val, entity_ident)

    # 2. Process manual free-text parameter inputs
    for obj_type, val, raw_ident in _extract_manual_parameter_objects(siemplify):
        _add_payload(obj_type, val, raw_ident)

    return payloads, entity_map


def start_blocklist_operation(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    action_start_time: int,
    suitable_entities: list[Any],
    result_data: dict[str, Any],
    is_add: bool = True,
) -> tuple[str, bool, int]:
    """Starts the blocklist operation during the first execution run."""
    description = extract_action_param(
        siemplify,
        param_name=PARAM_DESCRIPTION,
        is_mandatory=False,
    ) if is_add else None

    payloads, entity_map = build_blocklist_payloads(
        siemplify=siemplify,
        suitable_entities=suitable_entities,
        description=description,
        is_add=is_add,
    )

    if not payloads:
        action_verb = "added" if is_add else "removed"
        output_message = f"No supported entities or parameters were provided to be {action_verb}."
        siemplify.result.add_result_json({"added" if is_add else "removed": [], "failed": []})
        return output_message, False, EXECUTION_STATE_COMPLETED

    result_data.update({
        "result_urls": {},
        "json_results": {},
        "completed": [],
        "failed": [],
        "pending": [],
    })

    # Submit in chunks of PAYLOAD_CHUNK_SIZE
    for i in range(0, len(payloads), PAYLOAD_CHUNK_SIZE):
        chunk = payloads[i:i + PAYLOAD_CHUNK_SIZE]
        try:
            if is_add:
                responses = manager.add_entities_to_blocklist(chunk)
            else:
                responses = manager.remove_entities_from_blocklist(chunk)
        except Exception as e:
            siemplify.LOGGER.error(f"Error submitting blocklist batch: {e}")
            for item in chunk:
                for k, v in item.items():
                    if k != "description":
                        result_data["failed"].append(v)
            continue

        for item, response in zip(chunk, responses):
            item_val = next(v for k, v in item.items() if k != "description")
            if response.url:
                result_data["result_urls"][item_val] = response.url
                result_data["pending"].append(item_val)
            elif response.id:
                result_data["result_urls"][item_val] = response.id
                result_data["pending"].append(item_val)
            else:
                siemplify.LOGGER.error(
                    f"Failed to submit {item_val} to blocklist. Error: {response.error_message}"
                )
                result_data["failed"].append(item_val)

    if result_data["result_urls"]:
        return query_blocklist_operation_status(
            siemplify=siemplify,
            manager=manager,
            result_data=result_data,
            action_start_time=action_start_time,
            is_add=is_add,
        )

    # All failed directly on submit
    output_message, result_value = generate_blocklist_output_message_and_result(result_data, is_add=is_add)
    result_json_key = "added" if is_add else "removed"
    siemplify.result.add_result_json({result_json_key: result_data["completed"], "failed": result_data["failed"]})
    return output_message, result_value, EXECUTION_STATE_COMPLETED


def query_blocklist_operation_status(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    result_data: dict[str, Any],
    action_start_time: int,
    is_add: bool = True,
) -> tuple[str, bool, int]:
    """Queries asynchronous task status for pending blocklist operations."""
    results_urls = result_data.get("result_urls", {})
    action_verb = "added" if is_add else "removed"

    for entity_identifier, task_ref in list(results_urls.items()):
        if not task_ref:
            continue

        if is_async_action_global_timeout_approaching(siemplify, action_start_time) or is_approaching_timeout(
            action_start_time, DEFAULT_TIMEOUT
        ):
            pending_ids = [t_ref for t_ref in result_data["result_urls"].values() if t_ref]
            msg = (
                f"action ran into a timeout during execution. Pending tasks: {pending_ids}. "
                "Please increase the timeout in IDE."
            )
            raise TrendVisionOneTimeoutException(msg)

        task_url = task_ref if str(task_ref).startswith("http") else manager._get_full_url("get_task", task_id=task_ref)
        task_details = manager.get_task(task_url=task_url)

        result_data["json_results"][entity_identifier] = {
            "task_id": task_details.id,
            "status": task_details.status,
        }

        if task_details.status == SUCCESS_STATUS:
            siemplify.LOGGER.info(f"Successfully {action_verb} entity {entity_identifier}")
            result_data["result_urls"][entity_identifier] = None
            if entity_identifier not in result_data["completed"]:
                result_data["completed"].append(entity_identifier)
            if entity_identifier in result_data["pending"]:
                result_data["pending"].remove(entity_identifier)
        elif task_details.status in {FAILED_STATUS, REJECTED_STATUS}:
            result_data["result_urls"][entity_identifier] = None
            if entity_identifier not in result_data["failed"]:
                result_data["failed"].append(entity_identifier)
            if entity_identifier in result_data["pending"]:
                result_data["pending"].remove(entity_identifier)

    result_data["result_urls"] = {k: v for k, v in result_data["result_urls"].items() if v}

    if any(result_data["result_urls"].values()):
        pending_tasks = [v for v in result_data["result_urls"].values() if v]
        output_message = f"Pending tasks to finish: {', '.join(pending_tasks)}"
        result_value = json.dumps(result_data)
        return output_message, result_value, EXECUTION_STATE_INPROGRESS

    status = EXECUTION_STATE_COMPLETED

    result_json_key = "added" if is_add else "removed"
    if result_data["json_results"] or result_data["completed"] or result_data["failed"]:
        siemplify.result.add_result_json({result_json_key: result_data["completed"], "failed": result_data["failed"]})

    # Enrich entities
    completed_lower = {str(x).strip().lower() for x in result_data["completed"]}
    for entity in siemplify.target_entities:
        entity_identifier = get_entity_original_identifier(entity).strip()
        if entity_identifier in result_data["completed"] or entity_identifier.lower() in completed_lower:
            enrichment_key = f"{ENRICHMENT_PREFIX}_{IN_BLOCKLIST_KEY}"
            entity.additional_properties.update({enrichment_key: is_add})
            entity.is_enriched = True
    siemplify.update_entities(siemplify.target_entities)

    output_message, result_value = generate_blocklist_output_message_and_result(result_data, is_add=is_add)

    return output_message, result_value, status


def generate_blocklist_output_message_and_result(result_data: dict, is_add: bool = True) -> tuple[str, bool]:
    """Generates user-facing output message and boolean result."""
    action_verb = "added" if is_add else "removed"
    action_inf = "add" if is_add else "remove"
    result_value = True

    if result_data["completed"]:
        completed_str = ", ".join(result_data["completed"])
        output_message = (
            f"Successfully {action_verb} the following entities "
            f"{'to the' if is_add else 'from the'} blocklist in Trend Vision One: {completed_str}."
        )
        if result_data["failed"]:
            result_value = False
            failed_str = ", ".join(result_data["failed"])
            output_message += (
                f"\nAction wasn't able to {action_inf} the following entities in Trend Vision One: {failed_str}."
            )
    else:
        output_message = f"None of the provided entities were {action_verb} {'to' if is_add else 'from'} the blocklist in Trend Vision One."
        result_value = False

    return output_message, result_value


def execute_blocklist_action(
    is_first_run: bool,
    is_add: bool,
    script_name: str,
    action_display_name: str,
) -> None:
    """Executes main action lifecycle for blocklist addition or removal."""
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = script_name

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    result_value = False
    result_data: dict[str, Any] = {}
    status = EXECUTION_STATE_COMPLETED
    suitable_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type in SUPPORTED_BLOCKLIST_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        manager = TrendVisionOneManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )
        manager.test_connectivity()

        if is_first_run:
            output_message, result_value, status = start_blocklist_operation(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                suitable_entities=suitable_entities,
                result_data=result_data,
                is_add=is_add,
            )
        else:
            result_data = json.loads(extract_action_param(siemplify, param_name="additional_data", default_value="{}"))
            output_message, result_value, status = query_blocklist_operation_status(
                siemplify=siemplify,
                manager=manager,
                result_data=result_data,
                action_start_time=action_start_time,
                is_add=is_add,
            )

    except TrendVisionOneTimeoutException as e:
        output_message = f"{e}"
        status = EXECUTION_STATE_FAILED
        result_json_key = "added" if is_add else "removed"
        if result_data:
            siemplify.result.add_result_json({
                result_json_key: result_data.get("completed", []),
                "failed": result_data.get("failed", []),
            })
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = f'Error executing action "{action_display_name}". Reason: {e}'
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"\n  status: {status}\n  results: {result_value}\n  output_message: {output_message}")
    siemplify.end(output_message, result_value, status)

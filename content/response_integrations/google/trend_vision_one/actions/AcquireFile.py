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

"""Acquire File: collect a file from Trend Vision One endpoints and download the archive."""

from __future__ import annotations

import base64
import json
import math
import pathlib
import re
import sys
from http import HTTPStatus
from typing import TYPE_CHECKING

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler, unix_now
from TIPCommon import extract_action_param, extract_configuration_param, string_to_multi_value

from ..core.constants import (
    ACQUIRE_FILE_ACTION_NAME,
    ACQUIRE_FILE_DEADLINE_MARGIN_MS,
    ACQUIRE_FILE_MAX_ATTACHMENT_BYTES,
    ACQUIRE_FILE_PENDING_STATUSES,
    ACQUIRE_FILE_SCRIPT_NAME,
    ACQUIRE_FILE_TASK_DESCRIPTION,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    SUCCESS_STATUS,
)
from ..core.TrendVisionOneExceptions import TrendVisionOneTimeoutException
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.UtilsManager import (
    ErrorType,
    classify_exception,
    count_skipped_entities,
    get_endpoint_search_args,
    get_task_failure,
    log_action_result_summary,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

    from ..core.datamodels import Task


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
RESULT_SUCCESS = "success"
RESULT_FAILURE = "failure"
TIMEOUT_ERROR_MESSAGE = "Action ran into a timeout during execution."
TRANSIENT_ERROR_TYPES = (ErrorType.CONNECTION_ERROR, ErrorType.RATE_LIMITED, ErrorType.TIMEOUT)
MAX_DOWNLOAD_TIMEOUTS = 3
DOWNLOAD_TIMEOUT_MESSAGE = "The archive did not download in the script timeout. Increase the script timeout in the IDE."


def new_state() -> SingleJson:
    """Build an empty async state.

    Returns:
        The state. It has the requested file path, the target keys, the skipped entity count, the pending tasks
        by agent GUID, and the JSON result by target key.

    """
    return {"file_path": "", "keys": [], "skipped": 0, "pending": {}, "json_results": {}}


def build_failure_entry(
    error: str,
    error_type: str,
    agent_id: str | None,
    file_path: str,
    task_id: str | None = None,
) -> SingleJson:
    """Build the JSON result of a target that failed.

    Args:
        error: The failure message.
        error_type: The failure reason.
        agent_id: The agent GUID, if it is known.
        file_path: The requested file path.
        task_id: The collect file task ID, if a task exists.

    Returns:
        The entity result.

    """
    return {
        "status": RESULT_FAILURE,
        "error": error,
        "error_type": error_type,
        "agent_id": agent_id,
        "requested_file_path": file_path,
        "task_id": task_id,
    }


def record_result(state: SingleJson, keys: list[str], entry: SingleJson) -> None:
    """Save one entity result for each target key.

    Args:
        state: The async state.
        keys: The target keys (entity identifiers or Agent UUIDs) of one agent.
        entry: The entity result.

    """
    for key in keys:
        state["json_results"][key] = entry


def get_counts(state: SingleJson) -> tuple[int, int, list[str], int]:
    """Count the targets for the summary line.

    Args:
        state: The async state.

    Returns:
        The target count, the success count, one error type per failed target, and the skipped entity count.

    """
    results = state["json_results"].values()
    succeeded = sum(result["status"] == RESULT_SUCCESS for result in results)
    error_types = [result["error_type"] for result in results if result["status"] == RESULT_FAILURE]

    return len(state["keys"]), succeeded, error_types, state["skipped"]


def resolve_targets(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    state: SingleJson,
    lookups: dict[str, SingleJson],
) -> dict[str, list[str]]:
    """Find the agent GUID of each target. Save a failure for each target that has no endpoint.

    Args:
        siemplify: The action object.
        manager: The Trend Vision One manager.
        state: The async state.
        lookups: The endpoint search arguments by target key.

    Returns:
        The target keys by agent GUID. Targets with the same agent GUID share one task.

    """
    targets: dict[str, list[str]] = {}
    for key, lookup in lookups.items():
        agent_id = lookup.get("agent_id")
        try:
            endpoint = manager.search_endpoint(**lookup)
        except Exception as error:
            siemplify.LOGGER.exception(f"Failed to search the endpoint of {key}.")
            entry = build_failure_entry(str(error), classify_exception(error)[0], agent_id, state["file_path"])
            record_result(state, [key], entry)
            continue
        if endpoint is None or not endpoint.guid:
            message = f"Endpoint {key} was not found in {INTEGRATION_DISPLAY_NAME}."
            entry = build_failure_entry(message, ErrorType.ENDPOINT_NOT_FOUND, agent_id, state["file_path"])
            record_result(state, [key], entry)
            continue
        targets.setdefault(endpoint.guid, []).append(key)

    return targets


def start_task(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    state: SingleJson,
    guid: str,
    keys: list[str],
) -> None:
    """Start a collect file task on an agent. Save it as pending, or save a failure for its targets.

    Args:
        siemplify: The action object.
        manager: The Trend Vision One manager.
        state: The async state.
        guid: The agent GUID.
        keys: The target keys of the agent.

    """
    try:
        task_url = manager.collect_file(
            guid=guid,
            file_path=state["file_path"],
            description=ACQUIRE_FILE_TASK_DESCRIPTION,
        )
    except Exception as error:
        siemplify.LOGGER.exception(f"Failed to start the collect file task on agent {guid}.")
        entry = build_failure_entry(str(error), classify_exception(error)[0], guid, state["file_path"])
        record_result(state, keys, entry)
        return
    task_id = task_url.rstrip("/").rsplit("/", 1)[-1]
    state["pending"][guid] = {"task_url": task_url, "task_id": task_id, "keys": keys}


def start_acquisition(siemplify: SiemplifyAction, manager: TrendVisionOneManager, state: SingleJson) -> None:
    """Read the parameters, find the agents, and start one collect file task per agent.

    Args:
        siemplify: The action object.
        manager: The Trend Vision One manager.
        state: The async state to fill.

    """
    state["file_path"] = extract_action_param(siemplify, param_name="File Path", is_mandatory=True, print_value=True)
    agent_uuids = string_to_multi_value(extract_action_param(siemplify, param_name="Agent UUID", print_value=True))
    entities = [entity for entity in siemplify.target_entities if entity.entity_type in SUPPORTED_ENTITY_TYPES]
    lookups = {entity.identifier: get_endpoint_search_args(entity) for entity in entities}
    lookups.update({agent_uuid: get_endpoint_search_args(agent_uuid) for agent_uuid in agent_uuids})
    state["keys"] = list(lookups)
    state["skipped"] = count_skipped_entities(siemplify.target_entities, SUPPORTED_ENTITY_TYPES)
    if not lookups:
        return
    manager.test_connectivity()
    for guid, keys in resolve_targets(siemplify, manager, state, lookups).items():
        start_task(siemplify, manager, state, guid, keys)


def get_download_folder(siemplify: SiemplifyAction) -> pathlib.Path:
    """Get the folder for downloaded archives, and create it if it does not exist.

    Args:
        siemplify: The action object.

    Returns:
        The run folder of the action, or a downloads folder in the working directory if the run folder is not
        available.

    """
    try:
        folder = pathlib.Path(siemplify.run_folder)
    except (AttributeError, PermissionError, OSError):
        folder = pathlib.Path.cwd() / "downloads"
    folder.mkdir(parents=True, exist_ok=True)

    return folder


def build_file_name(task_id: str, file_path: str) -> str:
    """Build a safe local file name for a downloaded archive.

    Args:
        task_id: The collect file task ID.
        file_path: The path of the file on the endpoint (Windows or POSIX).

    Returns:
        The file name. It has only letters, digits, dots, hyphens, and underscores.

    """
    base_name = re.split(r"[\\/]", file_path)[-1][:200] or "collected_file"

    return re.sub(r"[^A-Za-z0-9._-]", "_", f"{task_id}_{base_name}.zip")


def attach_file(siemplify: SiemplifyAction, path: pathlib.Path) -> None:
    """Attach a downloaded archive to the case if it is not too large. Never raise.

    Args:
        siemplify: The action object.
        path: The local path of the archive.

    """
    try:
        size = path.stat().st_size
        if size > ACQUIRE_FILE_MAX_ATTACHMENT_BYTES:
            siemplify.LOGGER.info(f"{path.name} is not attached to the case. Size {size} bytes is over the limit.")
            return
        siemplify.result.add_attachment(
            title=f"Acquired Endpoint File - {path.name}",
            filename=path.name,
            file_contents=base64.b64encode(path.read_bytes()).decode(),
        )
    except Exception:
        siemplify.LOGGER.exception(f"Unable to attach {path.name} to the case.")


def download_file(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    state: SingleJson,
    guid: str,
    task: Task,
    max_seconds: float,
) -> SingleJson:
    """Download the archive of a succeeded task and build the success result.

    Args:
        siemplify: The action object.
        manager: The Trend Vision One manager.
        state: The async state.
        guid: The agent GUID.
        task: The succeeded collect file task.
        max_seconds: The time limit of the download, in seconds.

    Returns:
        The entity result.

    """
    raw_task = task.raw_data
    task_id = task.id or state["pending"][guid]["task_id"]
    requested_file_path = raw_task.get("filePath") or state["file_path"]
    destination = get_download_folder(siemplify) / build_file_name(task_id, requested_file_path)
    local_path = manager.download_collected_file(raw_task.get("resourceLocation"), str(destination), max_seconds)
    attach_file(siemplify, destination)

    return {
        "status": RESULT_SUCCESS,
        "action": ACQUIRE_FILE_ACTION_NAME,
        "agent_id": guid,
        "endpoint_name": raw_task.get("endpointName"),
        "file_path": local_path,
        "requested_file_path": requested_file_path,
        "download_path": local_path,
        "zip_password": raw_task.get("password"),
        "sha1": raw_task.get("fileSha1"),
        "sha256": raw_task.get("fileSha256"),
        "size": raw_task.get("fileSize"),
        "task_id": task_id,
        "created_at": raw_task.get("createdDateTime"),
        "completed_at": raw_task.get("lastActionDateTime"),
    }


def build_task_failure(state: SingleJson, guid: str, task: Task) -> SingleJson:
    """Build the result of a task that ended with failed, canceled, rejected, or an unknown status.

    Args:
        state: The async state.
        guid: The agent GUID.
        task: The collect file task.

    Returns:
        The entity result.

    """
    failure = get_task_failure(task)
    task_id = state["pending"][guid]["task_id"]

    return build_failure_entry(failure["error"], failure["error_type"], guid, state["file_path"], task_id)


def is_transient_error(error: Exception) -> bool:
    """Check if an error can go away on a later poll.

    Args:
        error: The exception from the task status check or the download.

    Returns:
        True for connection errors, rate limits, download time limits, and HTTP 5xx.

    """
    error_type, _, http_status = classify_exception(error)

    return error_type in TRANSIENT_ERROR_TYPES or (http_status or 0) >= HTTPStatus.INTERNAL_SERVER_ERROR


def poll_task(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    state: SingleJson,
    guid: str,
    max_seconds: float,
) -> None:
    """Check the task of one agent. Save the result of its targets if the task is done.

    A transient error keeps the task pending, so that the next poll tries again. A download that passes the run time
    limit 3 times fails the target.

    Args:
        siemplify: The action object.
        manager: The Trend Vision One manager.
        state: The async state.
        guid: The agent GUID.
        max_seconds: The time limit of the download, in seconds.

    """
    pending = state["pending"][guid]
    try:
        task = manager.get_task(task_url=pending["task_url"])
        if task.status in ACQUIRE_FILE_PENDING_STATUSES:
            return
        entry = (
            download_file(siemplify, manager, state, guid, task, max_seconds)
            if task.status == SUCCESS_STATUS
            else build_task_failure(state, guid, task)
        )
    except Exception as error:
        error_type = classify_exception(error)[0]
        if is_transient_error(error):
            if error_type == ErrorType.TIMEOUT:
                pending["download_timeouts"] = pending.get("download_timeouts", 0) + 1
            if pending.get("download_timeouts", 0) < MAX_DOWNLOAD_TIMEOUTS:
                siemplify.LOGGER.exception(f"Temporary error on the task of agent {guid}. The next poll tries again.")
                return
            message = DOWNLOAD_TIMEOUT_MESSAGE
        else:
            message = str(error)
        siemplify.LOGGER.exception(f"Failed to get the collected file of agent {guid}.")
        entry = build_failure_entry(message, error_type, guid, state["file_path"], pending["task_id"])
    record_result(state, pending["keys"], entry)
    del state["pending"][guid]


def get_pending_keys(state: SingleJson) -> list[str]:
    """Get the target keys that wait for a task.

    Args:
        state: The async state.

    Returns:
        The pending target keys.

    """
    return [key for pending in state["pending"].values() for key in pending["keys"]]


def build_output_message(state: SingleJson, succeeded: list[str], failed: list[str]) -> str:
    """Build the output message of a finished run.

    Args:
        state: The async state.
        succeeded: The target keys with a downloaded file.
        failed: The target keys that failed.

    Returns:
        The output message.

    """
    if not succeeded and not failed:
        return "No suitable entities or Agent UUIDs were found to acquire the file from."
    target = f'the file "{state["file_path"]}" on the following entities using {INTEGRATION_DISPLAY_NAME}'
    messages = []
    if succeeded:
        messages.append(f"Successfully acquired {target}: {', '.join(succeeded)}.")
    if failed:
        messages.append(f"Action wasn't able to acquire {target}: {', '.join(failed)}.")

    return "\n".join(messages)


def get_time_left_ms(deadline_ms: int) -> float:
    """Get the time left until a platform deadline, minus a safety margin.

    Args:
        deadline_ms: The deadline in Unix milliseconds, or 0 if the platform did not set one.

    Returns:
        The time left in milliseconds, or infinity if there is no deadline.

    """
    return deadline_ms - unix_now() - ACQUIRE_FILE_DEADLINE_MARGIN_MS if deadline_ms else math.inf


def poll_tasks(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    state: SingleJson,
) -> tuple[str, bool | str, int]:
    """Check all pending tasks, then save the state for the next poll or finish the action.

    If this run is close to its own deadline, the tasks that are not checked stay pending for the next poll.

    Args:
        siemplify: The action object.
        manager: The Trend Vision One manager.
        state: The async state.

    Returns:
        The output message, the result value (the serialized state if tasks are pending), and the execution state.

    Raises:
        TrendVisionOneTimeoutException: If pending targets cannot be polled again before the async deadline.

    """
    for guid in list(state["pending"]):
        time_left_ms = min(
            get_time_left_ms(siemplify.execution_deadline_unix_time_ms),
            get_time_left_ms(siemplify.async_total_duration_deadline),
        )
        if time_left_ms <= 0:
            siemplify.LOGGER.info("This run is close to its deadline. The next poll checks the remaining tasks.")
            break
        poll_task(siemplify, manager, state, guid, time_left_ms / 1000)
    if state["pending"]:
        polling_interval_ms = (siemplify.async_polling_interval_in_sec or 0) * 1000
        if get_time_left_ms(siemplify.async_total_duration_deadline) <= polling_interval_ms:
            raise TrendVisionOneTimeoutException(TIMEOUT_ERROR_MESSAGE)
        message = f"Waiting for results for the following endpoints: {', '.join(get_pending_keys(state))}"
        return message, json.dumps(state), EXECUTION_STATE_INPROGRESS
    results = state["json_results"]
    if results:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(results))
    succeeded = [key for key, result in results.items() if result["status"] == RESULT_SUCCESS]
    failed = [key for key, result in results.items() if result["status"] == RESULT_FAILURE]

    return build_output_message(state, succeeded, failed), bool(succeeded), EXECUTION_STATE_COMPLETED


def handle_run_error(siemplify: SiemplifyAction, state: SingleJson, error: Exception) -> tuple[str, bool, int]:
    """Fail the action. Attach the JSON result of finished targets and a failure for each unfinished target.

    Args:
        siemplify: The action object.
        state: The async state.
        error: The exception that ended the run.

    Returns:
        The output message, the result value, and the execution state.

    """
    is_timeout = isinstance(error, TrendVisionOneTimeoutException)
    unfinished = [key for key in state["keys"] if key not in state["json_results"]]
    tasks_by_key = {
        key: (guid, pending["task_id"]) for guid, pending in state["pending"].items() for key in pending["keys"]
    }
    error_type = classify_exception(error)[0]
    message = TIMEOUT_ERROR_MESSAGE if is_timeout else str(error)
    for key in unfinished:
        agent_id, task_id = tasks_by_key.get(key, (None, None))
        record_result(state, [key], build_failure_entry(message, error_type, agent_id, state["file_path"], task_id))
    if state["json_results"]:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(state["json_results"]))
    reason = str(error)
    if is_timeout:
        reason = (
            f"action ran into a timeout during execution. Pending endpoints: {', '.join(unfinished)}. "
            "Please increase the timeout in IDE and try again."
        )

    return f'Error executing action "{ACQUIRE_FILE_ACTION_NAME}". Reason: {reason}', False, EXECUTION_STATE_FAILED


def build_manager(siemplify: SiemplifyAction) -> TrendVisionOneManager:
    """Build the Trend Vision One manager from the integration configuration.

    Args:
        siemplify: The action object.

    Returns:
        The manager.

    """
    return TrendVisionOneManager(
        api_root=extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
        ),
        api_token=extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="API Token",
            is_mandatory=True,
            remove_whitespaces=False,
        ),
        verify_ssl=extract_configuration_param(
            siemplify,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            is_mandatory=False,
            default_value=True,
            input_type=bool,
            print_value=True,
        ),
        siemplify=siemplify,
    )


def load_state(siemplify: SiemplifyAction) -> SingleJson:
    """Load the async state that the previous run saved.

    Args:
        siemplify: The action object.

    Returns:
        The state, with defaults for missing keys.

    """
    saved_state: SingleJson = json.loads(
        extract_action_param(siemplify, param_name="additional_data", default_value="{}")
    )

    return {**new_state(), **saved_state}


def run_once(siemplify: SiemplifyAction, state: SingleJson, *, is_first_run: bool) -> tuple[str, bool | str, int]:
    """Start the tasks on the first run or load the saved state on a poll, then check the pending tasks.

    Args:
        siemplify: The action object.
        state: The async state. The function fills it in place, so that a failure can still report it.
        is_first_run: True for the first run, False for an async poll.

    Returns:
        The output message, the result value, and the execution state.

    """
    if not is_first_run:
        state.update(load_state(siemplify))
    manager = build_manager(siemplify)
    if is_first_run:
        start_acquisition(siemplify, manager, state)

    return poll_tasks(siemplify, manager, state)


@output_handler
def main(is_first_run: bool) -> None:
    """Run the Acquire File action.

    Args:
        is_first_run: True for the first run, False for an async poll.

    """
    siemplify = SiemplifyAction()
    siemplify.script_name = ACQUIRE_FILE_SCRIPT_NAME
    state = new_state()
    run_error = None
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        output_message, result_value, status = run_once(siemplify, state, is_first_run=is_first_run)
    except Exception as error:
        siemplify.LOGGER.exception(f"Error executing action {ACQUIRE_FILE_SCRIPT_NAME}.")
        run_error = error
        output_message, result_value, status = handle_run_error(siemplify, state, error)
    log_action_result_summary(siemplify, status, lambda: get_counts(state), error=run_error)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"\n  status: {status}\n  output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main(len(sys.argv) < 3 or sys.argv[2] == "True")

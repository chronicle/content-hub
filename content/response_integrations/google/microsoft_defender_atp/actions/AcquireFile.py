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

"""Acquire a file from Microsoft Defender for Endpoint machines via Live Response."""

from __future__ import annotations

import contextlib
import json
import ntpath
import os
import tempfile
import uuid
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.transformation import convert_dict_to_json_result_dict
from TIPCommon.utils import get_entity_original_identifier

from ..core import constants
from ..core.base_action import BaseAction
from ..core.constants import ErrorType
from ..core.exceptions import DefenderNotFoundException
from ..core.UtilsManager import (
    ActionResultSummaryInput,
    classify_exception,
    classify_live_response_failure,
    get_summary_scope,
    hash_acquired_file,
    log_action_result_summary,
    normalize_mde_file_path,
)

if TYPE_CHECKING:
    from typing import Never, NoReturn

    from TIPCommon.types import SingleJson


class AcquireFileAction(BaseAction):
    """Acquire one file per machine with the Live Response GetFile command."""

    # Live Response is a Defender API; a Graph-scoped token is rejected there.
    use_graph_api = False

    def __init__(self) -> None:
        """Initialize the Acquire File action and its result summary inputs."""
        super().__init__(constants.ACQUIRE_FILE_SCRIPT_NAME)
        self.state: SingleJson = {}
        self.target_results: dict[str, str | None] = {}
        self.run_error: Exception | None = None
        self.timeout_marker_due: bool = False
        self.summary_logged: bool = False

    def _extract_action_parameters(self) -> None:
        """Extract action parameters; File Path is only mandatory on the first run."""
        run_as_first_run = self.is_first_run
        self.params.machine_id = extract_action_param(self.soar_action, param_name="Machine ID", print_value=True)
        self.params.file_path = extract_action_param(
            self.soar_action,
            param_name="File Path",
            is_mandatory=run_as_first_run,
            print_value=True,
        )
        self.params.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            default_value=constants.ACQUIRE_FILE_DEFAULT_COMMENT,
            print_value=True,
        )
        self.params.additional_data = extract_action_param(
            self.soar_action,
            param_name="additional_data",
            default_value="{}",
        )

    def _perform_action(self, _: Never) -> None:
        """Start the acquisition on the first run, poll it on later runs."""
        if self.is_first_run:
            try:
                file_path = normalize_mde_file_path(self.params.file_path)
            except ValueError as error:
                self._set_failed(str(error), ErrorType.INVALID_INPUT)
                return
            target_count, unsupported_count = get_summary_scope(
                self.soar_action.target_entities,
                constants.ACQUIRE_FILE_ENTITY_TYPES,
                self.params.machine_id,
            )
            self.state = {
                "target_count": target_count,
                "unsupported_count": unsupported_count,
                "file_path": file_path,
                "comment": self.params.comment,
                "failed": {},
                "not_found": [],
                "targets": {},
                constants.ERROR_TYPES_STATE_KEY: {},
            }
            self._resolve_targets()
        else:
            self.state = json.loads(self.params.additional_data)
            if is_approaching_action_timeout(self.soar_action.async_total_duration_deadline):
                self._fail_pending_targets(
                    "Action ran into a timeout during execution. Please increase the timeout in IDE and try again.",
                    ErrorType.TIMEOUT,
                )
                self._finish_run()
                return

        for machine_id, target in self.state["targets"].items():
            if target["status"] == constants.LIVE_RESPONSE_WAITING_STATUS:
                self._dispatch(machine_id, target)
            elif target["status"] in constants.LIVE_RESPONSE_PENDING_STATUSES:
                self._poll(machine_id, target)
        self._finish_run()

    def _resolve_targets(self) -> None:
        """Resolve Machine ID (overrides entities) or HOSTNAME/ADDRESS entities."""
        if self.params.machine_id:
            lookups = [(self.params.machine_id, None)]
        else:
            lookups = [
                (get_entity_original_identifier(entity), entity.entity_type)
                for entity in self.soar_action.target_entities
                if entity.entity_type in constants.ACQUIRE_FILE_ENTITY_TYPES
            ]

        for identifier, entity_type in lookups:
            try:
                machine = (
                    self.api_client.get_machine_by_id(identifier)
                    if entity_type is None
                    else self.api_client.find_machine_for_entity(identifier, entity_type)
                )
            except DefenderNotFoundException:
                self.state["not_found"].append(identifier)
                continue
            except Exception as error:  # pylint: disable=broad-except
                self.logger.exception(error)
                self.state["failed"][identifier] = str(error)
                self.state[constants.ERROR_TYPES_STATE_KEY][identifier] = classify_exception(error)[0]
                continue

            target = self.state["targets"].setdefault(
                machine.id,
                {"entities": [], "status": constants.LIVE_RESPONSE_WAITING_STATUS, "action_id": None, "error": None},
            )
            target["entities"].append(machine.id if entity_type is None else identifier)

    def _dispatch(self, machine_id: str, target: SingleJson) -> None:
        """Adopt an identical active GetFile, wait for another active action, or start one.

        Args:
            machine_id: Defender machine ID.
            target: Mutable per-machine state.
        """
        try:
            active_actions = self.api_client.get_active_machine_actions(machine_id)
            action = next(filter(self._is_same_get_file, active_actions), None)
            if action is None and active_actions:
                self.logger.info(
                    f"Machine {machine_id} has active action {active_actions[0].get('id')}. Waiting for it to finish.",
                )
                return
            if action is None:
                action = self.api_client.run_live_response_command(
                    machine_id=machine_id,
                    commands=[self._get_file_command()],
                    comment=self.state["comment"],
                )
        except Exception as error:  # pylint: disable=broad-except
            self.logger.exception(error)
            self._fail_target(target, str(error), classify_exception(error)[0])
            return

        self.logger.info(f"Tracking GetFile action {action['id']} on machine {machine_id}.")
        target["action_id"] = action["id"]
        target["status"] = action.get("status") or "Pending"

    def _get_file_command(self) -> SingleJson:
        """Build the Live Response GetFile command for the requested path.

        Returns:
            The GetFile command object.
        """
        return {"type": "GetFile", "params": [{"key": "Path", "value": self.state["file_path"]}]}

    def _is_same_get_file(self, machine_action: SingleJson) -> bool:
        """Check whether an active machine action is a GetFile of the same path.

        Args:
            machine_action: Active machine action returned by Defender.

        Returns:
            True if the action fetches the requested path (case-insensitive).
        """
        commands = machine_action.get("commands") or [{}]
        command = commands[0].get("command")
        if not isinstance(command, dict) or command.get("type") != "GetFile":
            return False

        path = next((p.get("value") for p in command.get("params", []) if p.get("key") == "Path"), "")

        return str(path).lower() == self.state["file_path"].lower()

    def _poll(self, machine_id: str, target: SingleJson) -> None:
        """Refresh the status of a dispatched GetFile action.

        Args:
            machine_id: Defender machine ID.
            target: Mutable per-machine state.
        """
        try:
            action = self.api_client.get_live_response_status(target["action_id"])
        except Exception as error:  # pylint: disable=broad-except
            self.logger.exception(error)
            self._fail_target(target, str(error), classify_exception(error)[0])
            return

        target["status"] = action.get("status")
        if target["status"] in constants.SUCCESS_STATUSES:
            self._collect_file(machine_id, target, action)
        elif target["status"] not in constants.LIVE_RESPONSE_PENDING_STATUSES:
            errors = [str(error) for command in action.get("commands", []) for error in command.get("errors") or []]
            reason = "; ".join(errors) or f"Live Response action status: {target['status']}."
            self._fail_target(target, reason, classify_live_response_failure(target["status"], reason))

    def _collect_file(self, machine_id: str, target: SingleJson, action: SingleJson) -> None:
        """Download, hash, save and attach the acquired file.

        Args:
            machine_id: Defender machine ID.
            target: Mutable per-machine state.
            action: Succeeded Live Response machine action.
        """
        try:
            link = self.api_client.get_live_response_result_download_link(action["id"])
            raw = self.api_client.get_live_response_result(link["value"])
            hashes = hash_acquired_file(raw)
            download_path = self._save_file(raw, hashes["is_gzip"])
        except Exception as error:  # pylint: disable=broad-except
            self.logger.exception(error)
            self._fail_target(target, f"Failed to retrieve the acquired file: {error}", classify_exception(error)[0])
            return

        try:
            self.soar_action.add_attachment(download_path)
        except Exception as error:  # pylint: disable=broad-except
            # The SDK raises a bare Exception; the file is still saved locally.
            self.logger.warn(f"Failed to attach {download_path} to the case: {error}")

        target["result"] = {
            "action": constants.ACQUIRE_FILE_ACTION_NAME,
            "machine_id": machine_id,
            "file_path": self.state["file_path"],
            "file_name": ntpath.basename(self.state["file_path"]),
            "download_path": download_path,
            "md5": hashes["md5"],
            "sha1": hashes["sha1"],
            "sha256": hashes["sha256"],
            "size": hashes["size"],
            "status": "success",
            "created_at": action.get("creationDateTimeUtc"),
            "completed_at": action.get("lastUpdateDateTimeUtc"),
        }

    def _save_file(self, raw: bytes, is_gzip: bool) -> str:
        """Write the vendor artifact as-is under a random name.

        Args:
            raw: Downloaded file bytes.
            is_gzip: Whether the bytes are gzip-compressed.

        Returns:
            The local path of the saved file.
        """
        try:
            folder = self.soar_action.run_folder
        except (AttributeError, PermissionError, OSError):
            folder = tempfile.gettempdir()
        download_path = os.path.join(folder, f"{uuid.uuid4()}.{'gz' if is_gzip else 'bin'}")
        with open(download_path, "wb") as file:
            file.write(raw)

        return download_path

    def _fail_target(self, target: SingleJson, reason: str, error_type: str) -> None:
        """Mark a machine as failed.

        Args:
            target: Mutable per-machine state.
            reason: Failure reason reported in the output message.
            error_type: Failure error type reported in the JSON result.
        """
        self.logger.error(f"Failed to acquire file on {', '.join(target['entities'])}: {reason}")
        target["status"] = "Failed"
        target["error"] = reason
        target["error_type"] = error_type

    def _fail_pending_targets(self, reason: str, error_type: str) -> None:
        """Mark every machine whose acquisition has not finished as failed.

        Args:
            reason: Failure reason reported in the output message.
            error_type: Failure error type reported in the JSON result.
        """
        for target in self.state["targets"].values():
            if target["status"] in constants.LIVE_RESPONSE_PENDING_STATUSES:
                self._fail_target(target, reason, error_type)

    def _pending_entities(self) -> list[str]:
        """List the entities whose acquisition has not finished.

        Returns:
            Entity identifiers of machines that are still pending.
        """
        return [
            entity
            for target in self.state["targets"].values()
            if target["status"] in constants.LIVE_RESPONSE_PENDING_STATUSES
            for entity in target["entities"]
        ]

    def _set_failed(self, reason: str, error_type: str) -> None:
        """Fail the action run and add a failure JSON result entry per target.

        Args:
            reason: Error reason for the output message.
            error_type: Error type for each failure entry.
        """
        self.output_message = f'Error executing action "{constants.ACQUIRE_FILE_ACTION_NAME}". Reason: {reason}'
        self.result_value = False
        self.execution_state = ExecutionState.FAILED
        entries = self._build_failure_entries(self.output_message, error_type)
        self._set_target_results(entries)
        self.json_results = convert_dict_to_json_result_dict(entries)

    def _build_failure_entries(self, error: str, error_type: str) -> SingleJson:
        """Build JSON result failure entries for an action-level failure.

        Args:
            error: Error message to record for each target.
            error_type: Error type to record for each target.

        Returns:
            Failure entries keyed by Machine ID, supported entity identifiers,
            or the integration identifier when no target is available.
        """
        machine_id: str | None = getattr(self.params, "machine_id", None)
        if machine_id:
            keys = [machine_id]
        else:
            keys = [
                get_entity_original_identifier(entity)
                for entity in self.soar_action.target_entities
                if entity.entity_type in constants.ACQUIRE_FILE_ENTITY_TYPES
            ] or [constants.INTEGRATION_IDENTIFIER]

        return {key: {"status": "failure", "error": error, "error_type": error_type} for key in keys}

    def _set_target_results(self, entries: SingleJson) -> None:
        """Keep the error type of each JSON result entry for the result summary line.

        Args:
            entries: JSON result entries keyed by target. The integration identifier key is not a target.
        """
        self.target_results = {
            key: None if entry.get("status") == "success" else entry.get("error_type", ErrorType.UNKNOWN_ERROR)
            for key, entry in entries.items()
            if key != constants.INTEGRATION_IDENTIFIER
        }

    def _finish_run(self) -> None:
        """Keep polling while machines are pending, otherwise report the outcome."""
        file_path = self.state["file_path"]
        pending = self._pending_entities()
        if pending:
            self._request_timeout_marker()
            self.result_value = json.dumps(self.state)
            self.execution_state = ExecutionState.IN_PROGRESS
            self.output_message = (
                f'Waiting for file "{file_path}" to be acquired from the following endpoints: {", ".join(pending)}'
            )
            return

        results, failed, all_results = self._collect_outcomes()
        self.result_value = bool(results) and not failed
        self.output_message = self._build_output_message(file_path, results, failed)
        entries = all_results or self._build_failure_entries(self.output_message, ErrorType.INVALID_INPUT)
        self._set_target_results(entries)
        self.json_results = convert_dict_to_json_result_dict(entries)

    def _collect_outcomes(self) -> tuple[SingleJson, dict[str, str], SingleJson]:
        """Group the finished targets into successes, failures and JSON result entries.

        Returns:
            A tuple of (results, failed, all_results): the entity results of
            successful acquisitions, the failure reason per entity, and the
            JSON result entry per entity, including not-found endpoints.
        """
        targets = self.state["targets"].values()
        results = {e: t["result"] for t in targets if t.get("result") for e in t["entities"]}
        failed = {**self.state["failed"]}
        failed.update({e: t["error"] for t in targets if t["error"] for e in t["entities"]})
        error_types = {**self.state.get(constants.ERROR_TYPES_STATE_KEY, {})}
        error_types.update({e: t.get("error_type") for t in targets if t["error"] for e in t["entities"]})
        all_results = dict(results)
        for entity, reason in failed.items():
            error_type = error_types.get(entity) or ErrorType.UNKNOWN_ERROR
            all_results[entity] = {"status": "failure", "error": reason, "error_type": error_type}
        not_found_error = f"Endpoint was not found in {constants.INTEGRATION_IDENTIFIER}."
        for entity in self.state["not_found"]:
            all_results[entity] = {
                "status": "failure",
                "error": not_found_error,
                "error_type": ErrorType.ENDPOINT_NOT_FOUND,
            }

        return results, failed, all_results

    def _finalize_action_on_failure(self, error: Exception) -> None:
        """Send the JSON result when a raised error fails the action.

        If targets were already resolved (on this run or an earlier poll), their
        finished entries stay and unfinished targets fail with the error. If the
        saved state can't be used, every target gets a failure entry, so the
        original error is kept.

        Args:
            error: The exception caught by the base action run loop.
        """
        self.run_error = error
        error_type = classify_exception(error)[0]
        entries: SingleJson = {}
        try:
            if not self.state and not self.is_first_run:
                self.state = json.loads(self.params.additional_data)
            if self.state:
                self._fail_pending_targets(str(error), error_type)
                entries = self._collect_outcomes()[2]
        except Exception as state_error:  # pylint: disable=broad-except
            self.logger.exception(f"Failed to build the JSON result from the saved state: {state_error}")
            entries = {}
        entries = entries or self._build_failure_entries(str(error), error_type)
        self._set_target_results(entries)
        self.soar_action.result.add_result_json(convert_dict_to_json_result_dict(entries))

    def _finalize(self) -> None:
        """Log the result summary line once per finished run, or the one-time timeout marker."""
        state = ExecutionState.FAILED if self.run_error else self.execution_state
        is_marker = state == ExecutionState.IN_PROGRESS
        if self.summary_logged or (is_marker and not self.timeout_marker_due):
            return

        self.summary_logged = True
        log_action_result_summary(self.logger, lambda: self._build_summary_input(state, is_marker))

    def _build_summary_input(self, state: ExecutionState | int, is_marker: bool) -> ActionResultSummaryInput:
        """Build the summary inputs from the first-run scope or current target entities.

        Args:
            state: Final execution state, or IN_PROGRESS for the timeout marker.
            is_marker: Whether this summary is the one-time IN_PROGRESS timeout marker.

        Returns:
            Summary inputs for the result summary line.
        """
        machine_id: str | None = getattr(self.params, "machine_id", None)
        scope = get_summary_scope(self.soar_action.target_entities, constants.ACQUIRE_FILE_ENTITY_TYPES, machine_id)
        targets, skipped = self.state.get("target_count", scope[0]), self.state.get("unsupported_count", scope[1])
        unfinished = max(targets - len(self.target_results), 0) if self.run_error or is_marker else 0

        return ActionResultSummaryInput(
            execution_state=state,
            target_results=self.target_results,
            skipped=skipped,
            unfinished=unfinished,
            error=self.run_error,
            error_type=ErrorType.TIMEOUT if is_marker else None,
        )

    def _request_timeout_marker(self) -> None:
        """Request the one-time IN_PROGRESS timeout summary line if the next poll may miss the async deadline.

        A flag in the async state makes sure that the marker is logged once per action run.
        """
        try:
            deadline = int(self.soar_action.async_total_duration_deadline or 0)
            next_poll_time = unix_now() + int(self.soar_action.async_polling_interval_in_sec or 0) * 1000
            if self.state.get(constants.TIMEOUT_MARKER_STATE_KEY) or not 0 < deadline <= next_poll_time:
                return

            self.state[constants.TIMEOUT_MARKER_STATE_KEY] = True
            self.timeout_marker_due = True
            self._set_target_results(self._collect_outcomes()[2])
        except Exception as err:
            with contextlib.suppress(Exception):
                self.logger.warn(f"Failed to log timeout summary marker: {err}")

    def run(self) -> None:
        """Run the action and fail it with a JSON result on errors raised before the base run loop."""
        try:
            super().run()
        except Exception as error:  # pylint: disable=broad-except
            self._set_failed(str(error), classify_exception(error)[0])
            self.soar_action.result.add_result_json(self.json_results)
            self.run_error = error
            self._finalize()
            self.soar_action.end(
                message=self.output_message,
                result_value=self.result_value,
                execution_state=self.execution_state.value,
            )

    def _build_output_message(self, file_path: str, results: SingleJson, failed: dict[str, str]) -> str:
        """Build the SOAR-24 output message.

        Args:
            file_path: Acquired endpoint file path.
            results: Entity results of successful acquisitions.
            failed: Failure reason per entity.

        Returns:
            The output message.
        """
        product = constants.INTEGRATION_IDENTIFIER
        not_found = self.state["not_found"]
        lines = [f'None of the provided endpoints returned file "{file_path}".']
        if results:
            lines = [
                f'Successfully acquired file "{file_path}" from the following endpoints '
                f"using {product}: {', '.join(results)}.",
            ]
        if failed:
            lines.append(
                f'Action wasn\'t able to acquire file "{file_path}" from the following endpoints using {product}:',
            )
            lines.extend(f"{entity}: {reason}" for entity, reason in failed.items())
        if not_found:
            lines.append(f"The following endpoints were not found in {product}: {', '.join(not_found)}.")

        return "\n".join(lines)


def main() -> NoReturn:
    """Run the Acquire File action."""
    AcquireFileAction().run()


if __name__ == "__main__":
    main()

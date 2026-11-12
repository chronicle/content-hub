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

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.utils import get_entity_original_identifier
from ..core import constants
from ..core.base_action import BaseAction
from ..core.exceptions import (
    DefenderNotFoundException,
    DefenderException,
)
from ..core.MicrosoftDefenderATPManager import MicrosoftDefenderATPError

if TYPE_CHECKING:
    from typing import Never, NoReturn

    from soar_sdk.SiemplifyDataModel import DomainEntityInfo

    from TIPCommon.types import SingleJson

    from ..core.datamodels import Machine

    from ..core.MicrosoftDefenderATPManager import MicrosoftDefenderATPManager

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@dataclass(slots=True)
class ActionData:
    """
    Data class for holding action state
    """

    endpoints_data: dict[str, SingleJson] | None = None
    completed: list[str] | None = None
    failed: list[str] | None = None
    not_found: list[str] | None = None


class ExecuteLiveResponseCommandAction(BaseAction):
    def __init__(self) -> None:
        super().__init__(
            constants.EXECUTE_LIVE_RESPONSE_COMMAND_SCRIPT_NAME,
        )
        self._parsed_command: SingleJson | None = None

    @property
    def parsed_command(self) -> SingleJson:
        if self._parsed_command is None:
            self._parsed_command = json.loads(self.params.command)
        return self._parsed_command

    def _extract_action_parameters(self) -> None:
        self.params.command = extract_action_param(
            self.soar_action,
            param_name="Command",
            is_mandatory=True,
            print_value=True,
        )
        self.params.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            print_value=True,
        )
        self.params.additional_data = extract_action_param(
            self.soar_action,
            param_name="additional_data",
            default_value="{}",
        )

    def _get_suitable_entities(self) -> list[DomainEntityInfo]:
        """
        Get entities suitable for command execution.
        """
        return [
            entity
            for entity in self.soar_action.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

    def _perform_action(self, _: Never) -> None:
        self._set_action_data()

        if self.action_data.endpoints_data is None:
            suitable_entities: list[DomainEntityInfo] = (
                self._get_suitable_entities()
            )

            if not suitable_entities:
                self.output_message = (
                    "No suitable entities found to run the command on."
                )
                self.result_value = False
                return

            self._initialize_action_data()
            self.handle_entities(suitable_entities)

            if self.action_data.endpoints_data is None:
                self._finish_operation()
                return

            self._initiate_commands()
            self.logger.info(
                "Waiting for 5 seconds before checking command status."
            )
            time.sleep(5)

        self._query_command_status()
        self._handle_command_progress()

    def _set_action_data(self) -> None:
        self.action_data = (
            ActionData(**json.loads(self.params.additional_data))
            if self.params.additional_data
            else ActionData()
        )

    def handle_entities(
        self,
        suitable_entities: list[DomainEntityInfo],
    ) -> None:
        """
        Process a list of entities to find their corresponding endpoints.
        """
        for entity in suitable_entities:
            self._process_entity(entity)

    def _initialize_action_data(self) -> None:
        """Initialize empty action tracking structure."""
        self.action_data = ActionData(
            endpoints_data={},
            completed=[],
            failed=[],
            not_found=[],
        )

    def _process_entity(self, entity: DomainEntityInfo) -> None:
        """Resolve entity to endpoint and update tracking info."""
        entity_identifier: str = get_entity_original_identifier(entity)

        try:
            machine: Machine = self._get_machine(entity, entity_identifier)
            self._record_machine(entity_identifier, machine)

        except (DefenderNotFoundException, MicrosoftDefenderATPError):
            self._handle_not_found(entity_identifier)

        except DefenderException as e:
            self._handle_failure(entity_identifier, e)

    def _get_machine(
        self,
        entity: DomainEntityInfo,
        entity_identifier: str,
    ) -> Machine:
        """
        Retrieve machine by IP or hostname based on entity type.
        """
        if entity.entity_type == EntityTypes.ADDRESS:
            return self._get_machine_by_ip(entity_identifier)

        return self._get_machine_by_hostname(entity_identifier)

    def _get_machine_by_ip(self, ip_address: str):
        """
        Get a single machine by its IP address.
        """
        machines = self.api_client.get_machines(ip=ip_address)
        if not machines:
            raise DefenderNotFoundException(f"Machine with IP {ip_address} not found.")
        return machines[-1]

    def _get_machine_by_hostname(self, hostname: str):
        """
        Get a single machine by its hostname.
        """
        machines = self.api_client.get_machines_by_name(starts_with_name=hostname)
        if not machines:
            raise DefenderNotFoundException(
                f"Machine with hostname {hostname} not found."
            )
        return machines[-1]

    def _record_machine(self, identifier: str, machine: Machine) -> None:
        """Store machine details for command execution."""
        if machine.id not in self.action_data.endpoints_data:
            self.action_data.endpoints_data[machine.id] = {
                "identifiers": [identifier],
                "status": "Pending",
                "machine_details": machine.to_json(),
                "action_id": None,
                "result": None,
                "waiting_for_action_id": None,
                "error": None,
            }
        else:
            self.action_data.endpoints_data[machine.id]["identifiers"].append(
                identifier
            )

    def _handle_not_found(self, identifier: str) -> None:
        """Log and record missing machine."""
        self.logger.info(f"Machine for entity {identifier} was not found. Skipping...")
        self.action_data.not_found.append(identifier)

    def _handle_failure(self, identifier: str, error: Exception) -> None:
        """Log and record machine fetch failure."""
        self.logger.error(f"An error occurred on entity {identifier}: {error}")
        self.logger.exception(error)
        self.action_data.failed.append(identifier)

    def _serialize_command_params(self, params: list[SingleJson]) -> list[tuple]:
        """
        Serialize parameter dictionaries into a sorted list of sorted key-value tuples.

        Args:
            params (list[SingleJson]): List of parameter dictionaries.

        Returns:
            list[tuple]: Sorted list of parameter tuples.
        """
        serialized = []
        for p in params:
            if isinstance(p, dict):
                serialized.append(tuple(sorted((str(k), str(v)) for k, v in p.items())))
        return sorted(serialized)

    def _are_commands_equal(self, cmd1: SingleJson, cmd2: SingleJson) -> bool:
        """Check if two commands have identical parameters."""
        if not isinstance(cmd1, dict) or not isinstance(cmd2, dict):
            return False
        if cmd1.get("type") != cmd2.get("type"):
            return False

        params1 = cmd1.get("params", [])
        params2 = cmd2.get("params", [])

        if len(params1) != len(params2):
            return False

        return (
            self._serialize_command_params(params1)
            == self._serialize_command_params(params2)
        )

    def _find_existing_action(
        self,
        active_actions: list[SingleJson],
        command: SingleJson,
    ) -> SingleJson | None:
        """Generic method to check if an active action exists with same command."""
        for active_action in active_actions:
            active_commands = active_action.get("commands", [])
            if not active_commands:
                continue
            if self._are_commands_equal(
                command, active_commands[0].get("command")
            ):
                return active_action
        return None

    def _initiate_command_for_machine(
        self, machine_id: str, data: SingleJson
    ) -> None:
        """Initiate command or establish conflict/waiting resolution."""
        command = self.parsed_command
        active_actions: list[SingleJson] = []
        try:
            active_actions = self.api_client.get_active_machine_actions(
                machine_id
            )
        except (MicrosoftDefenderATPError, DefenderException) as e:
            self.logger.error(
                f"Failed to check active actions for machine {machine_id}: {e}"
            )

        if active_actions:
            self._handle_existing_machine_actions(
                machine_id, data, active_actions, command
            )
            return

        self._execute_new_command(machine_id, data, command)

    def _handle_existing_machine_actions(
        self,
        machine_id: str,
        data: SingleJson,
        active_actions: list[SingleJson],
        command: SingleJson,
    ) -> None:
        matching_action = self._find_existing_action(
            active_actions, command
        )
        if matching_action:
            self._adopt_active_action(machine_id, data, matching_action)
        else:
            conflicting_id = active_actions[0].get("id")
            self._set_waiting_for_action(machine_id, data, conflicting_id)

    def _adopt_active_action(
        self, machine_id: str, data: SingleJson, matching_action: SingleJson
    ) -> None:
        matching_action_id = matching_action.get("id")
        self.logger.info(
            f"Same command is already running on machine "
            f"{machine_id} (active action ID: "
            f"{matching_action_id}). Adopting this action ID."
        )
        data["action_id"] = matching_action_id
        data["status"] = matching_action.get("status")
        data["error"] = None
        data["waiting_for_action_id"] = None

    def _set_waiting_for_action(
        self, machine_id: str, data: SingleJson, conflicting_action_id: str
    ) -> None:
        self.logger.info(
            f"A different command is running on machine "
            f"{machine_id} (active action ID: "
            f"{conflicting_action_id}). Waiting for it to finish."
        )
        data["status"] = "Waiting"
        data["waiting_for_action_id"] = conflicting_action_id
        data["error"] = None

    def _execute_new_command(
        self, machine_id: str, data: SingleJson, command: SingleJson
    ) -> None:
        try:
            action_info = self.api_client.run_live_response_command(
                machine_id=machine_id,
                commands=[command],
                comment=self.params.comment,
            )
            data["action_id"] = action_info.get("id")
            data["status"] = "InProgress"
            data["error"] = None
            data["waiting_for_action_id"] = None
            identifiers_str = ", ".join(data["identifiers"])
            self.logger.info(
                "Live response command initiated for machine associated "
                f"with entities {identifiers_str} "
                f"with action ID: {data['action_id']}"
            )
        except MicrosoftDefenderATPError as e:
            self._handle_failure(", ".join(data["identifiers"]), e)
            data["status"] = "Failed"
            data["error"] = str(e)

    def _initiate_commands(self) -> None:
        """Trigger live response command for each machine."""
        for machine_id, data in self.action_data.endpoints_data.items():
            self._initiate_command_for_machine(machine_id, data)

    def _query_command_status(self) -> None:
        """Check command progress, handle completion or timeout."""
        self._validate_action_timeout()

        for machine_id, data in self.action_data.endpoints_data.items():
            if data["status"] in constants.FINISHED_STATUSES:
                continue

            if data["status"] == "Waiting":
                self._check_waiting_status(machine_id, data)
                continue

            if not data.get("action_id"):
                continue

            self._update_action_progress(machine_id, data)

    def _check_waiting_status(self, machine_id: str, data: SingleJson) -> None:
        waiting_id = data.get("waiting_for_action_id")
        if not waiting_id:
            self.logger.error(
                f"Machine {machine_id} is in Waiting status but "
                "lacks a waiting_id. Marking as Failed."
            )
            data["status"] = "Failed"
            data["error"] = "Waiting for an unknown action ID"
            return
        try:
            waiting_status = self.api_client.get_live_response_status(
                waiting_id
            )
            if waiting_status.get("status") in constants.FINISHED_STATUSES:
                self.logger.info(
                    f"The active action {waiting_id} we were waiting "
                    f"for has finished on machine {machine_id}. "
                    "Initiating our command now."
                )
                self._initiate_command_for_machine(machine_id, data)
        except MicrosoftDefenderATPError as e:
            self.logger.error(
                f"Failed to check status of waiting action "
                f"{waiting_id}: {e}"
            )

    def _update_action_progress(self, machine_id: str, data: SingleJson) -> None:
        try:
            action_status = self.api_client.get_live_response_status(
                data["action_id"]
            )
            data["status"] = action_status.get("status")
            data["result"] = action_status

            if data["status"] in constants.FINISHED_STATUSES:
                self._process_finished_command(
                    machine_id, data, action_status
                )

        except MicrosoftDefenderATPError as e:
            self._handle_failure(", ".join(data["identifiers"]), e)
            data["status"] = "Failed"
            data["error"] = str(e)

    def _extract_command_failure_reason(self, action_status: SingleJson) -> str:
        """Extract failure reason from commands results list."""
        command_errors = []
        for cmd in action_status.get("commands", []):
            if cmd.get("status") == "Failed":
                results = cmd.get("results", {})
                if isinstance(results, dict):
                    error_msg = (
                        results.get("error")
                        or results.get("errorMessage")
                        or results.get("message")
                    )
                    if error_msg:
                        command_errors.append(str(error_msg))
        return (
            ", ".join(command_errors)
            if command_errors
            else "Command failed to execute"
        )

    def _process_finished_command(
        self,
        machine_id: str,
        data: SingleJson,
        action_status: SingleJson,
    ) -> None:
        """Process a command that has finished execution."""
        entity_identifiers = data["identifiers"]
        self._record_endpoint_status(entity_identifiers, data["status"])
        self.logger.info(
            f"Finished command execution on machine {machine_id} for entities "
            f"{', '.join(entity_identifiers)}. "
            f"Action status response from API: {json.dumps(action_status)}"
        )

        command = self.parsed_command

        if not self._is_successful(data["status"]):
            error_details = self._extract_command_failure_reason(action_status)
            data["error"] = error_details

            self.logger.error(
                f"The command failed to execute on machine {machine_id} for "
                f"entities {', '.join(entity_identifiers)}. "
                f"Error: {error_details}. "
                f"Action status: {json.dumps(action_status)}"
            )
            return

        if self._is_get_file_command(command):
            self._handle_get_file_command(
                machine_id=machine_id,
                data=data,
                action_status=action_status,
                command=command,
                entity_identifiers=entity_identifiers,
            )
            return

        self._handle_generic_success(action_status, data)

    def _is_successful(self, status: str) -> bool:
        return status in constants.SUCCESS_STATUSES

    def _is_get_file_command(self, command: SingleJson) -> bool:
        return command.get("type") == "GetFile"

    def _handle_get_file_command(
        self,
        *,
        machine_id: str,
        data: SingleJson,
        action_status: SingleJson,
        command: SingleJson,
        entity_identifiers: list[str],
    ) -> None:
        try:
            file_content = self._download_file_content(data["action_id"])
            file_path = self._persist_downloaded_file(
                machine_id=machine_id,
                data=data,
                command=command,
                file_content=file_content,
            )

            self.soar_action.add_attachment(file_path)
            action_status["results"] = {"filepath": file_path}
            data["result"] = action_status

        except (MicrosoftDefenderATPError, IOError) as exc:
            self._handle_get_file_failure(machine_id, entity_identifiers, data, exc)

    def _download_file_content(self, action_id: str) -> bytes:
        download_link_info = (
            self.api_client.get_live_response_result_download_link(action_id)
        )
        return self.api_client.get_live_response_result(
            download_link_info.get("value")
        )

    def _persist_downloaded_file(
        self,
        *,
        machine_id: str,
        data: SingleJson,
        command: SingleJson,
        file_content: bytes,
    ) -> str:
        machine_name = data["machine_details"].get("computerDnsName", machine_id)
        original_file_path = self._extract_original_file_path(command)
        sanitized_path = self._sanitize_file_path(original_file_path)

        file_name = f"{machine_name}_{sanitized_path}"
        file_path = os.path.join(self.soar_action.run_folder, file_name)

        with open(file_path, "wb") as file_handle:
            file_handle.write(file_content)

        return file_path

    def _extract_original_file_path(self, command: SingleJson) -> str:
        file_path_param: SingleJson | None = next(
            (p for p in command.get("params", []) if p.get("key") == "Path"),
            None,
        )
        return file_path_param["value"] if file_path_param else "downloaded_file"

    def _sanitize_file_path(self, file_path: str) -> str:
        sanitized = file_path.replace(":\\", "_").replace("\\", "_").replace("/", "_")
        _, ext = os.path.splitext(sanitized)
        if not ext:
            sanitized += ".txt"
        return sanitized

    def _handle_get_file_failure(
        self,
        machine_id: str,
        entity_identifiers: list[str],
        data: SingleJson,
        exc: Exception,
    ) -> None:
        self.logger.error(
            f"Failed to download file for machine {machine_id} "
            f"(entities: {', '.join(entity_identifiers)}): {exc}"
        )
        self.logger.exception(exc)
        data["status"] = "Failed"
        self._record_endpoint_status(entity_identifiers, "Failed")

    def _handle_generic_success(
        self,
        action_status: SingleJson,
        data: SingleJson,
    ) -> None:
        command_results = action_status.get("commands", [])
        if not command_results:
            return

        action_status["results"] = command_results[0].get("results")
        data["result"] = action_status

    def _validate_action_timeout(self) -> None:
        """Raise an exception if the async timeout is about to be hit."""
        if not self._is_approaching_async_timeout():
            return

        pending_entities_str: str = ", ".join(self._get_pending_entities())
        raise DefenderException(
            "Error executing action "
            f"“{constants.EXECUTE_LIVE_RESPONSE_COMMAND_SCRIPT_NAME}”. "
            "Reason: action ran into a timeout during execution. "
            f"Pending endpoints: {pending_entities_str}. Note: the endpoints will be "
            "started again during the action re-run. "
            "Please increase the timeout in IDE."
        )

    def _record_endpoint_status(
        self,
        entity_identifiers: list[str],
        status: str,
    ) -> None:
        """Record endpoint as completed or failed based on its status."""
        completed = self.action_data.completed
        failed = self.action_data.failed

        is_success = status in constants.SUCCESS_STATUSES

        add_to = completed if is_success else failed
        remove_from = failed if is_success else completed

        for identifier in entity_identifiers:
            if identifier not in add_to:
                add_to.append(identifier)
            if identifier in remove_from:
                remove_from.remove(identifier)

    def _handle_command_progress(self) -> None:
        """Continue or finalize action based on pending entities."""
        if self._get_pending_entities():
            self._set_action_in_progress()
        else:
            self._finish_operation()

    def _get_pending_entities(self) -> list[str]:
        return [
            identifier
            for data in self.action_data.endpoints_data.values()
            for identifier in data["identifiers"]
            if data["status"] not in constants.FINISHED_STATUSES
        ]

    def _set_action_in_progress(self) -> None:
        self.result_value = json.dumps(asdict(self.action_data))
        pending_entities: list[str] = self._get_pending_entities()
        self.output_message = (
            "Waiting for command to finish on the following entities: "
            f"{', '.join(pending_entities)}"
        )
        self.execution_state = ExecutionState.IN_PROGRESS

    def _finish_operation(self) -> None:
        """Finalize the action, summarize results, and set output values."""
        completed: list[str] | None = self.action_data.completed
        failed: list[str] | None = self.action_data.failed
        not_found: list[str] | None = self.action_data.not_found
        pending: list[str] = self._get_pending_entities()

        self._set_json_result()

        messages = [
            self._format_completed_message(completed),
            self._format_failed_message(failed),
            self._format_not_found_message(not_found),
        ]

        output_message: str = "\n".join(filter(None, messages)).strip()

        if not output_message:
            output_message = "No endpoints were processed."

        is_success = bool(completed) and not (failed or pending)

        self.output_message = output_message
        self.result_value = is_success

    def _format_completed_message(self, completed: list[str]) -> str:
        """Return formatted message for successfully processed endpoints."""
        if not completed:
            return ""

        return (
            "Successfully executed command on the following endpoints in "
            "Microsoft Defender for Endpoint: "
            f"{', '.join(completed)}."
        )

    def _format_failed_message(self, failed: list[str]) -> str:
        """Return formatted message for failed endpoints."""
        if not failed and not self._get_pending_entities():
            return ""

        all_failed = failed + self._get_pending_entities()

        return (
            "The command didn’t complete for the following endpoints in Microsoft "
            f"Defender for Endpoint: {', '.join(sorted(list(set(all_failed))))}."
        )

    def _format_not_found_message(self, not_found: list[str]) -> str:
        """Return formatted message for entities not found."""
        if not not_found:
            return ""

        return (
            "The following entities were not found in Microsoft Defender for Endpoint: "
            f"{', '.join(not_found)}."
        )

    def _set_json_result(self) -> None:
        """
        Set the JSON result for the action.
        """
        json_results = []
        for endpoint_data in self.action_data.endpoints_data.values():
            if endpoint_data.get("result"):
                for identifier in endpoint_data.get("identifiers", []):
                    json_results.append(
                        {
                            "Entity": identifier,
                            "EntityResult": endpoint_data["result"],
                        }
                    )
        self.json_results = json_results

    def _is_approaching_async_timeout(self) -> bool:
        """
        Determine whether the action approaches asynchronous timeout.
        """
        return is_approaching_action_timeout(
            self.soar_action.async_total_duration_deadline,
        )


def main() -> NoReturn:
    ExecuteLiveResponseCommandAction().run()


if __name__ == "__main__":
    main()

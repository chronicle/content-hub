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
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.utils import get_entity_original_identifier
from TIPCommon.transformation import string_to_multi_value

from ..core.base_action import BaseAction
from ..core import constants
from ..core.exceptions import XDRNotFoundException, XDRException

if TYPE_CHECKING:
    from typing import NoReturn

    from soar_sdk.SiemplifyDataModel import DomainEntityInfo

    from TIPCommon.types import SingleJson

    from ..core.datamodels import Endpoint


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@dataclass(slots=True)
class ActionData:
    """
    Data class for holding action state
    """
    action_id: str = ""
    endpoints_data: dict[str, SingleJson] | None = None
    completed: list[str] | None = None
    failed: list[str] | None = None
    not_found: list[str] | None = None


class ScanEndpointAction(BaseAction):
    def __init__(self) -> None:
        super().__init__(constants.SCAN_ENDPOINT_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.incident_id = extract_action_param(
            self.soar_action,
            param_name="Incident ID",
            print_value=True,
        )
        agent_ids_str = extract_action_param(
            self.soar_action,
            param_name="Agent ID",
            is_mandatory=False,
            print_value=True,
            default_value="",
        )
        self.params.agent_ids = string_to_multi_value(
            string_value=agent_ids_str,
            only_unique=True,
        )
        self.params.additional_data = extract_action_param(
            self.soar_action,
            param_name="additional_data",
            default_value="{}",
        )

    def _perform_action(self, _) -> None:
        suitable_entities: list[DomainEntityInfo] = [
            entity for entity in self.soar_action.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        if not suitable_entities and not self.params.agent_ids:
            self.output_message: str = (
                "No suitable entities or agent IDs were provided to scan."
            )
            self.result_value = False
            return

        self._set_action_data()

        if not self.action_data.action_id:
            self._start_scan(suitable_entities)
        else:
            self._query_scan_status()

    def _set_action_data(self) -> None:
        self.action_data = (
            ActionData(**json.loads(self.params.additional_data))
            if self.params.additional_data
            else ActionData()
        )

    def _start_scan(self, suitable_entities: list[DomainEntityInfo]) -> None:
        self._initialize_action_data()

        for entity in suitable_entities:
            self._process_entity(entity)

        for agent_id in self.params.agent_ids:
            if not self._is_valid_agent_id(agent_id):
                self.logger.info(
                    f"Invalid Agent ID format: '{agent_id}'. Skipping."
                )
                self.action_data.failed.append(agent_id)
                continue
            self._record_agent_id(agent_id)

        if not self.action_data.endpoints_data:
            self._finish_operation()
            return

        self._initiate_scan()

    def _is_valid_agent_id(self, agent_id: str) -> bool:
        """
        Validate the format of a Palo Alto Cortex XDR Agent ID.
        A valid agent ID is a 32-character hexadecimal string.
        """
        return bool(constants.AGENT_ID_VALIDATION_REGEX.fullmatch(agent_id))

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
            endpoint: Endpoint = self._get_endpoint(entity, entity_identifier)
            self._record_endpoint(entity_identifier, endpoint)

        except XDRNotFoundException:
            self._handle_not_found(entity_identifier)

        except XDRException as e:
            self._handle_failure(entity_identifier, e)

    def _get_endpoint(
        self,
        entity: DomainEntityInfo,
        entity_identifier: str,
    ) -> Endpoint:
        """Retrieve endpoint by IP or hostname based on entity type."""
        if entity.entity_type == EntityTypes.ADDRESS:
            return self.api_client.get_endpoint_by_ip(entity_identifier)

        return self.api_client.get_endpoint_by_hostname(entity_identifier)

    def _record_endpoint(self, identifier: str, endpoint: Endpoint) -> None:
        """Store endpoint details for scanning."""
        self.action_data.endpoints_data[endpoint.endpoint_id]: SingleJson = {
            "identifier": identifier,
            "status": "Pending",
            "details": endpoint.to_json(),
        }

    def _record_agent_id(self, agent_id: str) -> None:
        if agent_id in self.action_data.endpoints_data:
            self.logger.info(
                f"Agent ID {agent_id} corresponds to an endpoint "
                f"already found via a target entity. Skipping."
            )
            return

        self.logger.info(f"Adding agent ID {agent_id} to the scan list.")
        self.action_data.endpoints_data[agent_id]: SingleJson = {
            "identifier": agent_id,
            "status": "Pending",
            "details": {},
        }

    def _handle_not_found(self, identifier: str) -> None:
        """Log and record missing endpoint."""
        self.logger.info(f"Endpoint for entity {identifier} was not found. Skipping...")
        self.action_data.not_found.append(identifier)

    def _handle_failure(self, identifier: str, error: Exception) -> None:
        """Log and record endpoint fetch failure."""
        self.logger.error(f"An error occurred on entity {identifier}: {error}")
        self.logger.exception(error)
        self.action_data.failed.append(identifier)

    def _initiate_scan(self) -> None:
        """Trigger scan and handle partial responses."""
        endpoint_ids: list[str] = list(self.action_data.endpoints_data)
        scan_reply: SingleJson = self.api_client.scan_endpoints(
            endpoint_ids=endpoint_ids,
            incident_id=self.params.incident_id,
        )

        self.action_data.action_id = scan_reply.get("action_id")
        scanned_count: int = scan_reply.get("endpoints_count", constants.NULL_VALUE)

        if scanned_count < len(endpoint_ids):
            self._handle_omitted_endpoints(endpoint_ids, scanned_count)

        self.logger.info(f"Scan started with action ID: {self.action_data.action_id}")
        self._query_scan_status()

    def _handle_omitted_endpoints(
        self,
        endpoint_ids: list[str],
        scanned_endpoints_count: int,
    ) -> None:
        """
        Handles endpoints that were not accepted by the API for scanning.
        """

        action_status: SingleJson = self.api_client.get_action_status(
            self.action_data.action_id
        )
        accepted_endpoint_ids: list[str] = action_status.get("data", {}).keys()
        omitted_endpoint_ids: set[str] = set(endpoint_ids) - set(accepted_endpoint_ids)

        self.logger.info(
            f"API only accepted {scanned_endpoints_count} of "
            f"{len(endpoint_ids)} endpoints for scanning. The remaining "
            "endpoints will be marked as failed."
        )
        for endpoint_id in omitted_endpoint_ids:
            if endpoint_id in self.action_data.endpoints_data:
                entity_identifier: str = self.action_data.endpoints_data[endpoint_id][
                    "identifier"
                ]
                self.action_data.endpoints_data[endpoint_id]["status"] = "Failed"
                self.action_data.failed.append(entity_identifier)

    def _query_scan_status(self) -> None:
        """Check scan progress, handle completion or timeout."""
        self._validate_scan_timeout()
        if not self._has_valid_action():
            return

        statuses: SingleJson = self._fetch_action_status()
        self._update_endpoint_statuses(statuses)
        self._handle_scan_progress()

    def _validate_scan_timeout(self) -> None:
        """Raise an exception if the async timeout is about to be hit."""
        if not self._is_approaching_async_timeout():
            return

        pending_entities_str: str = ", ".join(self._get_pending_entities())
        raise XDRException(
            f"Error executing action “{constants.SCAN_ENDPOINT_SCRIPT_NAME}”. "
            "Reason: action ran into a timeout during execution. "
            f"Pending endpoints: {pending_entities_str}. "
            "Note: the scan will be started again during the action re-run. "
            "Please increase the timeout in IDE."
        )

    def _has_valid_action(self) -> bool:
        """Check whether there is an active action to track."""
        if self.action_data.action_id:
            return True

        self.output_message: str = "No action to track."
        self.result_value: bool = False
        self.execution_state: ExecutionState = ExecutionState.FAILED

        return False

    def _fetch_action_status(self) -> SingleJson:
        """Fetch current scan status for the action."""
        return self.api_client.get_action_status(self.action_data.action_id) or {}

    def _update_endpoint_statuses(self, statuses: SingleJson) -> None:
        """Update each endpoint’s current status."""
        for endpoint_id, status in statuses.get("data", {}).items():
            if endpoint_id not in self.action_data.endpoints_data:
                continue

            endpoint_data: SingleJson = self.action_data.endpoints_data[endpoint_id]
            endpoint_data["status"] = status

            entity_identifier: str = endpoint_data["identifier"]
            self._record_endpoint_status(entity_identifier, status)

    def _record_endpoint_status(self, entity_identifier: str, status: str) -> None:
        """Record endpoint as completed or failed based on its status."""
        if status not in constants.FINISHED_STATUSES:
            return

        completed: list[str] | None
        failed: list[str] | None
        completed, failed = self.action_data.completed, self.action_data.failed

        if status == constants.SUCCESS_STATUS:
            if entity_identifier not in completed:
                completed.append(entity_identifier)
        else:
            if entity_identifier not in failed:
                failed.append(entity_identifier)

    def _handle_scan_progress(self) -> None:
        """Continue or finalize scan based on pending entities."""
        if self._get_pending_entities():
            self._set_action_in_progress()

        else:
            self._finish_operation()

    def _get_pending_entities(self) -> list[str]:
        return [
            data["identifier"] for data in self.action_data.endpoints_data.values()
            if data["status"] not in constants.FINISHED_STATUSES
        ]

    def _set_action_in_progress(self) -> None:
        pending_entities: list[str] = self._get_pending_entities()
        self.output_message: str = (
            "Waiting for scan to finish on the following entities: "
            f"{', '.join(pending_entities)}"
        )
        self.result_value: str = json.dumps(asdict(self.action_data))
        self.execution_state: ExecutionState = ExecutionState.IN_PROGRESS

    def _finish_operation(self) -> None:
        """Finalize the scan action, summarize results, and set output values."""
        completed: list[str] | None = self.action_data.completed
        failed: list[str] | None = self.action_data.failed
        not_found: list[str] | None = self.action_data.not_found
        pending: list[str] = self._get_pending_entities()

        self._set_json_result()

        messages: list[str] = [
            self._format_completed_message(completed),
            self._format_failed_message(failed),
            self._format_not_found_message(not_found),
        ]

        output_message: str = "\n".join(filter(None, messages)).strip()

        if not output_message:
            output_message = "No endpoints were scanned."

        is_success: bool = bool(completed) and not (failed or pending)

        self.output_message: str = output_message
        self.result_value = is_success

    def _format_completed_message(self, completed: list[str]) -> str:
        """Return formatted message for successfully scanned endpoints."""
        if not completed:
            return (
                "The scan didn't complete for all of the provided "
                "endpoints in Palo Alto XDR."
            )

        return (
            "Successfully scanned the following endpoints in Palo Alto XDR: "
            f"{', '.join(completed)}."
        )

    def _format_failed_message(self, failed: list[str]) -> str:
        """Return formatted message for failed endpoint scans."""
        if not failed:
            return ""

        return (
            "The scan didn't complete for the following endpoints in Palo Alto XDR: "
            f"{', '.join(failed)}."
        )

    def _format_not_found_message(self, not_found: list[str]) -> str:
        """Return formatted message for entities not found in XDR."""
        if not not_found:
            return ""

        return (
            "The following entities were not found in Palo Alto XDR: "
            f"{', '.join(not_found)}."
        )

    def _set_json_result(self) -> None:
        """
        Set the JSON result for the action.
        """
        json_results: list[SingleJson] = [
            {
                "Entity": endpoint_data["identifier"],
                "EntityResult": endpoint_data["details"],
            }
            for endpoint_data in self.action_data.endpoints_data.values()
        ]
        self.json_results = json_results

    def _is_approaching_async_timeout(self) -> bool:
        """
        Determine whether the action approaches asynchronous timeout.
        """
        return is_approaching_action_timeout(
            self.soar_action.async_total_duration_deadline,
        )


def main() -> NoReturn:
    ScanEndpointAction().run()


if __name__ == "__main__":
    main()

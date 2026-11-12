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

from dataclasses import dataclass
import json
from typing import  Any, TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import EntityTypes

from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import get_entity_original_identifier

from ..core.base_action import BaseAction
from ..core.constants import (
    DEFAULT_MAX_VULNERABILITIES, DEFAULT_SORT_BY,
    DEFAULT_SORT_ORDER,
    GET_MACHINE_VULNERABILITIES_SCRIPT_NAME,
    MAX_VULNERABILITIES_TO_RETURN,
    MIN_VULNERABILITIES_TO_RETURN,
)
from ..core.datamodels import Machine, Vulnerability
from ..core.exceptions import DefenderException, DefenderNotFoundException
from ..core.MicrosoftDefenderATPManager import MicrosoftDefenderATPValidationError

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import EntityInfo

    from TIPCommon.types import SingleJson


SUPPORTED_ENTITY_TYPES: list[str]= [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@dataclass(slots=True)
class ActionData:
    """Data class for holding action state"""
    completed: list[str]
    failed: list[str]
    not_found: list[str]
    json_results: list[SingleJson]


class GetMachineVulnerabilities(BaseAction):
    def __init__(self) -> None:
        super().__init__(GET_MACHINE_VULNERABILITIES_SCRIPT_NAME)
        self.action_data: ActionData = ActionData(
            completed=[],
            failed=[],
            not_found=[],
            json_results=[],
        )
        self.output_message: str = ""
        self.result_value: bool = True

    def _extract_action_parameters(self) -> None:
        self.params.severity_filter = extract_action_param(
            self.soar_action,
            param_name="Severity Filter",
            print_value=True,
            default_value="Critical",
        )
        self.params.threat_filter = extract_action_param(
            self.soar_action,
            param_name="Threat Filter",
            print_value=True,
        )
        self.params.sort_by = extract_action_param(
            self.soar_action,
            param_name="Sort By",
            default_value=DEFAULT_SORT_BY,
            print_value=True,
        )
        self.params.sort_order = extract_action_param(
            self.soar_action,
            param_name="Sort Order",
            default_value=DEFAULT_SORT_ORDER,
            print_value=True,
        )
        self.params.max_vulnerabilities_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Vulnerabilities To Return",
            input_type=int,
            default_value=DEFAULT_MAX_VULNERABILITIES,
            print_value=True,
            is_mandatory=True,
        )

    def _validate_params(self) -> None:
        if not (
            MIN_VULNERABILITIES_TO_RETURN
            <= self.params.max_vulnerabilities_to_return
            <= MAX_VULNERABILITIES_TO_RETURN
        ):
            raise ValueError(
                f'"Max Vulnerabilities To Return" must be a value between 1 and 100. '
                f"Provided value: {self.params.max_vulnerabilities_to_return}"
            )

    def _perform_action(self, _: Any) -> None:
        suitable_entities: list["EntityInfo"] = [
            entity
            for entity in self.soar_action.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        if not suitable_entities:
            self.output_message: str = "No suitable entities found."
            self.result_value: bool = False
            return

        severities: list[str]
        threats: list[str]
        severities, threats = self._validate_and_get_filters()

        for entity in suitable_entities:
            self.process_entity(entity, severities, threats)

        self._finalize_operation()

    def process_entity(
        self,
        entity: "EntityInfo",
        severities: list[str],
        threats: list[str],
    ) -> None:
        """Processes a single entity to find associated machine vulnerabilities.

        Args:
            entity (EntityInfo): The entity to process.
            severities list(str): A list of vulnerability severities to filter by.
            threats list(str): A list of threat names to filter by.
        """
        entity_identifier: str = get_entity_original_identifier(entity)
        self.logger.info(f"Started processing entity: {entity_identifier}")

        try:
            machine: Machine | None = self._get_machine(entity, entity_identifier)
            if machine is None:
                self._handle_not_found(entity_identifier)
                return

            self.logger.info(
                f"Found machine {machine.id} for entity {entity_identifier}"
            )
            vulnerabilities: list[Vulnerability] = self._get_vulnerabilities(
                machine,
                severities,
                threats,
            )

            if vulnerabilities:
                self._handle_success(entity_identifier, vulnerabilities)
            else:
                self.logger.info(
                    f"No vulnerabilities were found for machine {machine.id}"
                )
                self._handle_no_vulnerabilities_found(entity_identifier)

        except DefenderException as e:
            self._handle_failure(entity_identifier, e)

        finally:
            self.logger.info(f"Finished processing entity: {entity_identifier}")

    def _get_machine(
        self,
        entity: "EntityInfo",
        entity_identifier: str,
    ) -> Machine | None:
        """Retrieves a machine based on the entity type and identifier.

        Args:
            entity (EntityInfo): The entity object.
            entity_identifier (str): The original identifier of the entity.

        Returns:
            Machine | None: The found machine object, or None if not found.
        """
        try:
            if entity.entity_type == EntityTypes.ADDRESS:
                return self._get_machine_by_ip(entity_identifier)
            return self._get_machine_by_hostname(entity_identifier)

        except DefenderNotFoundException:
            return None

    def _get_machine_by_ip(self, ip_address: str) -> Machine:
        """Retrieves a machine by its IP address.

        Args:
            ip_address (str): The IP address of the machine.

        Return:
           machine(Machine): The most recently seen machine object matching the IP.

        Raises:
            DefenderNotFoundException: If the machine is not found.
        """
        machines: list[Machine] = self.api_client.get_machines(ip=ip_address) or []
        if not machines:
            raise DefenderNotFoundException(f"Machine with IP {ip_address} not found.")

        return max(machines, key=lambda machine: machine.last_seen_unix)

    def _get_machine_by_hostname(self, hostname: str) -> Machine:
        """Retrieves a machine by its hostname.

        Args:
            hostname (str): The hostname of the machine.

        Return:
            machine(Machine) : The most recently seen machine matching the exact
            hostname.

        Raises:
            DefenderNotFoundException: If the machine is not found.
        """
        machines: list[Machine] = (
            self.api_client.get_machines_by_name(starts_with_name=hostname) or []
        )
        if not machines:
            raise DefenderNotFoundException(
                f"Machine with hostname {hostname} not found."
            )
        return max(machines, key=lambda machine: machine.last_seen_unix)

    def _get_vulnerabilities(
        self,
        machine: Machine,
        severities: list[str],
        threats: list[str],
    ) -> list[Vulnerability]:
        """Retrieves vulnerabilities for a given machine,filtered by
        severity and threat.

        Args:
            machine (Machine): The machine object.
            severities (list[str]): A list of vulnerability severities to filter by.
            threats (list[str]): A list of threat names to filter by.

        Returns:
            list[Vulnerability]: A list of found vulnerabilities.
        """
        return self.api_client.get_machine_vulnerabilities(
            machine_id=machine.id,
            severities=severities,
            threats=threats,
            sort_by=self.params.sort_by,
            sort_order=self.params.sort_order,
            limit=self.params.max_vulnerabilities_to_return,
        )

    def _validate_and_get_filters(self) -> tuple[list[str], list[str]]:
        """Validates the action parameters and returns the filters to be used for the
        API call.
        """
        try:
            self.api_client.validate_sort_order(self.params.sort_order)

        except MicrosoftDefenderATPValidationError:
            self.logger.info(
                f"Invalid value provided for 'Sort Order': {self.params.sort_order}. "
                f"Defaulting to '{DEFAULT_SORT_ORDER}'."
            )
            self.params.sort_order = DEFAULT_SORT_ORDER

        threats: list[str] = self.api_client.convert_comma_separated_to_list(
            self.params.threat_filter
        )
        if threats:
            try:
                self.api_client.validate_threats(*threats)

            except MicrosoftDefenderATPValidationError:
                self.logger.info(
                    "Invalid value provided for 'Threat Filter': "
                    f"{self.params.threat_filter}. Ignoring this filter."
                )
                threats: list[str] = []

        severities: list[str] = self.api_client.convert_comma_separated_to_list(
            self.params.severity_filter
        )
        if severities:
            try:
                self.api_client.validate_severities(*severities)

            except MicrosoftDefenderATPValidationError:
                self.logger.info(
                    "Invalid value provided for 'Severity Filter': "
                    f"{self.params.severity_filter}. Ignoring this filter."
                )
                severities: list[str] = []

        try:
            if self.params.sort_by:
                self.api_client.validate_sort_by(self.params.sort_by)

        except MicrosoftDefenderATPValidationError:
            self.logger.info(
                f"Invalid value provided for 'Sort By': {self.params.sort_by}. "
                "Ignoring this filter."
            )
            self.params.sort_by = None

        return severities, threats

    def _handle_success(
        self,
        identifier: str,
        vulnerabilities: list[Vulnerability],
    ) -> None:
        """Handles the success meaages for the given entity.

        Args:
            identifier (str): The entityare found for the given entity.
            vulnerabilities (list[Vulnerability]): A list of vulnerabilities.
        """
        self.action_data.completed.append(identifier)
        self.action_data.json_results.append(
            {
                "Entity": identifier,
                "EntityResult": [v.to_json() for v in vulnerabilities],
            }
        )

    def _handle_no_vulnerabilities_found(self, identifier: str) -> None:
        """Handles the case where no vulnerabilities are found for a specific entity."""
        self.action_data.completed.append(identifier)

    def _handle_not_found(self, identifier: str) -> None:
        """Handles the case where the machine is not found for the given entity."""
        self.logger.info(f"Machine for entity {identifier} was not found. Skipping...")
        self.action_data.not_found.append(identifier)

    def _handle_failure(self, identifier: str, error: Exception) -> None:
        """Handles the case where an error occurs on the given entity."""
        self.logger.error(f"An error occurred on entity {identifier}: {error}")
        self.logger.exception(error)
        self.action_data.failed.append(identifier)

    def _finalize_operation(self) -> None:
        """Finalizes the operation and updates the action data."""
        completed: list[str] = self.action_data.completed
        failed: list[str] = self.action_data.failed
        not_found: list[str] = self.action_data.not_found

        is_success: bool = bool(completed) and not failed

        if not completed:
            self.output_message = (
                "The action wasn’t able to return vulnerabilities for the "
                "provided endpoints in Microsoft Defender for Endpoint."
            )
            self.result_value: bool = is_success
            return

        if completed and not self.action_data.json_results and not failed:
            self.output_message = (
                "No vulnerabilities were found for the provided "
                "endpoints in Microsoft Defender for Endpoint."
            )
            self.result_value: bool = True
            return

        messages: list[str] = [
            self._format_completed_message(completed),
            self._format_failed_message(failed),
            self._format_not_found_message(not_found),
        ]

        output_message: str = "\n".join(filter(None, messages)).strip()

        if self.action_data.json_results:
            self.soar_action.result.add_result_json(
                json.dumps(self.action_data.json_results)
            )
        self.output_message: str = output_message
        self.result_value: bool = is_success

    def _format_completed_message(self, completed: list[str]) -> str:
        """Formats the completed message.

        Args:
            completed (list[str]): A list of completed entities.

        Returns:
            str: The formatted completed message.
        """
        if not completed:
            return ""

        unique_completed: list[str] = sorted(list(set(completed)))

        v_found_entity_identifiers: set[str | None] = set(
            result.get("Entity") for result in self.action_data.json_results
        )

        v_found_entities: list[str] = [
            ent for ent in unique_completed if ent in v_found_entity_identifiers
        ]
        no_v_entities: list[str] = [
            ent for ent in unique_completed if ent not in v_found_entity_identifiers
        ]

        messages: list[str] = []
        if v_found_entities:
            messages.append(
                "Successfully returned vulnerabilities for the following "
                "endpoints in Microsoft Defender for Endpoint: "
                f"{', '.join(v_found_entities)}."
            )
        if no_v_entities:
            messages.append(
                "No vulnerabilities were found for the following endpoints in "
                f"Microsoft Defender for Endpoint: {', '.join(no_v_entities)}."
            )

        return "\n".join(messages)

    def _format_failed_message(self, failed: list[str]) -> str:
        """Formats the failed message.

        Args:
            failed (list[str]): A list of failed entities.

        Returns:
            str: The formatted failed message.
        """
        if not failed:
            return ""
        unique_failed: list[str] = sorted(list(set(failed)))

        return (
            "The action wasn’t able to return vulnerabilities for the "
            "following endpoints in Microsoft Defender for Endpoint: "
            f"{', '.join(unique_failed)}."
        )

    def _format_not_found_message(self, not_found: list[str]) -> str:
        """Formats the not found message.

        Args:
            not_found (list[str]): A list of not found entities.

        Returns:
            str: The formatted not found message.
        """
        if not not_found:
            return ""
        unique_not_found: list[str] = sorted(list(set(not_found)))

        return (
            "The action wasn’t able to return vulnerabilities for the "
            "following endpoints in Microsoft Defender for Endpoint: "
            f"{', '.join(unique_not_found)}."
        )


def main() -> None:
    GetMachineVulnerabilities().run()


if __name__ == "__main__":
    main()

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

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import EntityTypes

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import (
    convert_dict_to_json_result_dict,
    string_to_multi_value,
)

from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    ENTITIES_MAPPER,
    HIDE_HOST_SCRIPT_NAME,
    INTEGRATION_NAME,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import CrowdStrikeError
from crowd_strike_falcon.core.datamodels import Device
from crowd_strike_falcon.core.utils import get_entity_original_identifier, validate_device_id

if TYPE_CHECKING:
    from typing import Never, NoReturn

    from TIPCommon.types import SingleJson


class HideHostsAction(Action):
    def __init__(self) -> None:
        super().__init__(HIDE_HOST_SCRIPT_NAME)
        self.successful_entities: list[str] = []
        self.failed_entities: list[str] = []
        self.devices_to_hide: list[Device] = []

    def _extract_action_parameters(self) -> None:
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Root",
            default_value=API_ROOT_DEFAULT,
        )
        self.params.client_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client API ID",
        )
        self.params.client_secret = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client API Secret",
        )
        self.params.use_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            is_mandatory=True,
        )
        integration_cid = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Customer ID",
            print_value=True,
        )
        action_cid = extract_action_param(
            self.soar_action,
            param_name="Customer ID",
            print_value=True,
        )
        self.params.customer_id = action_cid or integration_cid
        self.params.hostnames = string_to_multi_value(
            extract_action_param(
                self.soar_action,
                param_name="Hostname",
                print_value=True,
            ),
        )
        device_id_param = extract_action_param(
            self.soar_action,
            param_name="Device ID",
            print_value=True,
        )
        self.params.device_ids = string_to_multi_value(device_id_param)

    def _validate_params(self) -> None:
        device_id_param = extract_action_param(
            self.soar_action,
            param_name="Device ID",
            print_value=True,
        )
        validate_device_id(device_id_param)

    def _init_api_clients(self) -> CrowdStrikeManager:
        return CrowdStrikeManager(
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            use_ssl=self.params.use_ssl,
            api_root=self.params.api_root,
            customer_id=self.params.customer_id,
            logger=self.logger,
        )

    def _perform_action(self, _: Never) -> None:
        target_entities = [
            entity
            for entity in self.soar_action.target_entities
            if entity.entity_type in ENTITIES_MAPPER
        ]

        if not target_entities and not self.params.hostnames and not self.params.device_ids:
            self.output_message = "None of the provided hosts were hidden."
            self.result_value = False
            return

        for entity in target_entities:
            self._find_and_stage_host(
                identifier=get_entity_original_identifier(entity),
                entity_type=entity.entity_type,
            )

        for hostname in self.params.hostnames:
            self._find_and_stage_host(
                identifier=hostname, entity_type=EntityTypes.HOSTNAME
            )

        for device_id in self.params.device_ids:
            self._stage_host_by_device_id(device_id)

        if self.devices_to_hide:
            self._execute_bulk_hide()

        self._finalize_output()

    def _find_and_stage_host(self, identifier: str, entity_type: str) -> None:
        """
        Finds a device by its identifier and type, and stages its ID for hiding.
        """
        if identifier in self.successful_entities or identifier in self.failed_entities:
            return

        device = self._get_device(identifier, entity_type)

        if not device:
            self.failed_entities.append(identifier)
            return

        existing_device = next((d for d in self.devices_to_hide if d.device_id == device.device_id), None)
        if existing_device:
            self.logger.info(
                f"Identifier '{identifier}' maps to device ID '{device.device_id}', which is already "
                f"associated with entity '{existing_device.original_identifier}'. Skipping duplication."
            )
            return

        device.original_identifier = identifier
        self.devices_to_hide.append(device)
        self.successful_entities.append(identifier)

    def _get_device(self, identifier: str, entity_type: str) -> Device | None:
        """
        Queries the CrowdStrike API for a device based on an identifier and type.
        Returns the device object on success, None on failure or if not found.
        """
        try:
            request_filter: SingleJson = {
                key: identifier for key in ENTITIES_MAPPER[entity_type]
            }
            request_filter["cid"] = self.params.customer_id

            devices: list[Device] = self.api_client.search_devices(**request_filter)
            if devices:
                return devices[0]

            self.logger.info(f"No device found for host {identifier}. Skipping.")
            return None

        except CrowdStrikeError as e:
            self.logger.error(f"An error occurred on host: {identifier}.")
            self.logger.exception(e)
            return None

    def _stage_host_by_device_id(self, device_id: str) -> None:
        """
        Finds a device by its ID and stages it for hiding.
        """
        if device_id in self.successful_entities or device_id in self.failed_entities:
            return

        device = self._get_device_by_id(device_id)

        if not device:
            self.failed_entities.append(device_id)
            return

        existing_device = next((d for d in self.devices_to_hide if d.device_id == device.device_id), None)
        if existing_device:
            self.logger.info(
                f"Identifier '{device_id}' maps to device ID '{device.device_id}', which is already "
                f"associated with entity '{existing_device.original_identifier}'. Skipping duplication."
            )
            return

        device.original_identifier = device_id
        self.devices_to_hide.append(device)
        self.successful_entities.append(device_id)

    def _get_device_by_id(self, device_id: str) -> Device | None:
        """
        Queries the CrowdStrike API for a device by its ID.
        Returns the device object on success, None on failure or if not found.
        """
        try:
            devices: list[Device] = self.api_client.get_devices(devices_ids=[device_id])
            if devices:
                return devices[0]

            self.logger.info(f"No device found for device ID {device_id}. Skipping.")
            return None

        except CrowdStrikeError as e:
            self.logger.error(f"An error occurred on device ID: {device_id}.")
            self.logger.exception(e)
            return None

    def _execute_bulk_hide(self) -> None:
        """
        Executes the API call to hide all staged device IDs.
        Handles API errors by moving entities from successful to failed.
        """
        unique_device_ids: list[str] = list(
            {device.device_id for device in self.devices_to_hide}
        )
        try:
            self.api_client.hide_hosts_by_device_ids(unique_device_ids)
            self.logger.info(
                f"Successfully sent request to hide {len(unique_device_ids)} devices."
            )
        except CrowdStrikeError as e:
            self.logger.error(f"Failed to hide hosts. Error: {e}")
            self.failed_entities.extend(self.successful_entities)
            self.successful_entities.clear()

    def _build_output_message(self) -> str:
        """Constructs the final output message based on the action's results."""
        output_parts: list[str] = []
        if self.successful_entities:
            output_parts.append(
                "Successfully hid the following hosts in Crowdstrike: "
                f"{', '.join(self.successful_entities)}."
            )

        if self.failed_entities:
            output_parts.append(
                "Action wasn’t able to hide the following hosts in Crowdstrike: "
                f"{', '.join(set(self.failed_entities))}."
            )

        return "\n".join(output_parts)

    def _finalize_output(self) -> None:
        """Sets the final result value and output message for the action."""
        self.output_message = self._build_output_message()

        json_results: SingleJson = {}
        if self.successful_entities:
            device_map = {device.device_id: device for device in self.devices_to_hide}

            for device in self.devices_to_hide:
                if device.device_id in device_map:
                    json_results[device.original_identifier] = device_map[
                        device.device_id
                    ].to_json()

            self.soar_action.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

        self.result_value = bool(self.successful_entities)
        if not self.successful_entities:
            self.result_value = False
            self.output_message = "None of the provided hosts were hidden."


def main() -> NoReturn:
    HideHostsAction().run()


if __name__ == "__main__":
    main()

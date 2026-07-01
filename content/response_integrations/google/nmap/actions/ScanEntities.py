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
from typing import NoReturn

from soar_sdk.SiemplifyDataModel import EntityTypes

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value, convert_list_to_comma_string
from TIPCommon.types import SingleJson
from TIPCommon.utils import get_entity_original_identifier
from ..core import constants
from ..core.NmapManager import NmapManager, NmapScanResult
from ..core import utils


class ScanEntities(Action):
    def __init__(self) -> None:
        super().__init__(constants.SCAN_ENTITIES_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = (
            f'Error executing action "{constants.SCAN_ENTITIES_SCRIPT_NAME}".'
        )
        self.result_value: bool = True
        self.json_results: list[SingleJson] = []
        self.successful_scans: list[str] = []
        self.failed_scans: list[str] = []
        self.supported_entity_types: list[str] = [
            EntityTypes.HOSTNAME,
            EntityTypes.ADDRESS,
            EntityTypes.DOMAIN,
        ]
        self.scan_results: SingleJson = {}
        self.in_scope_entities: list[str] = []
        self.enriched_entities: list[str] = []

    def _extract_action_parameters(self) -> None:
        self.params.ip_address = extract_action_param(
            self.soar_action,
            param_name="IP Address",
            print_value=True,
        )
        self.params.hostname = extract_action_param(
            self.soar_action,
            param_name="Hostname",
            print_value=True,
        )
        self.params.options = extract_action_param(
            self.soar_action,
            param_name="Options",
            print_value=True,
            is_mandatory=True,
        )
        self.params.ip_address = string_to_multi_value(
            string_value=self.params.ip_address,
            only_unique=True,
        )
        self.params.hostname = string_to_multi_value(
            string_value=self.params.hostname,
            only_unique=True,
        )

    def _init_api_clients(self) -> NmapManager:
        return NmapManager(self.soar_action)

    def _validate_params(self) -> None:
        utils.validate_ip_address(self.params.ip_address)
        utils.validate_nmap_root_required_options(self.params.options)

    def _perform_action(self, _) -> None:
        self.in_scope_entities = self._get_in_scope_entities()
        targets = self._gather_targets()

        self._run_scans(targets)
        self._build_output_messages()
        self._set_json_results()
        self._enrich_entities()
        self.result_value = bool(self.successful_scans)

    def _get_in_scope_entities(self) -> list[str]:
        return [
            get_entity_original_identifier(entity)
            for entity in self.soar_action.target_entities
            if entity.entity_type in self.supported_entity_types
        ]

    def _gather_targets(self) -> list[str]:
        return self.params.ip_address + self.params.hostname + self.in_scope_entities

    def _run_scans(self, targets: list[str]) -> None:
        for target in targets:
            nmap_scan_result: NmapScanResult = self.api_client.run_nmap_scan(
                target=target,
                options=self.params.options,
            )

            if (
                constants.ERROR_MESSAGE_FOR_INVALID_TARGET
                in nmap_scan_result.command_result.stderr.upper()
                or not nmap_scan_result.parsed_result.to_dict()
            ):
                self.failed_scans.append(target)
            else:
                self.successful_scans.append(target)
                self.scan_results[target] = {
                    "json_data": nmap_scan_result.parsed_result.to_dict(),
                    "enrichment_data": nmap_scan_result.parsed_result.to_enrichment(),
                }

    def _build_output_messages(self) -> None:
        if self.successful_scans and self.failed_scans:
            self.output_message = (
                "Successfully scanned the following entities using Nmap: "
                f"{convert_list_to_comma_string(self.successful_scans)}.\n"
                "No information was found for the following entities: "
                f"{convert_list_to_comma_string(self.failed_scans)}."
            )
        elif self.successful_scans:
            self.output_message = (
                "Successfully scanned the following entities using Nmap: "
                f"{convert_list_to_comma_string(self.successful_scans)}."
            )
        elif self.failed_scans:
            self.output_message = (
                "No information was found for the following entities: "
                f"{convert_list_to_comma_string(self.failed_scans)}."
            )
        else:
            self.output_message = "No entities were provided for scanning."

    def _set_json_results(self) -> None:
        if not self.scan_results:
            return

        result_list: list[SingleJson] = [
            {"Entity": target, "EntityResult": data["json_data"]}
            for target, data in self.scan_results.items()
        ]
        self.json_results = result_list

    def _enrich_entities(self) -> None:
        for entity in self.soar_action.target_entities:
            if entity.entity_type not in self.supported_entity_types:
                continue
            original_id = get_entity_original_identifier(entity)
            if original_id in self.scan_results:
                entity.additional_properties.update(
                    self.scan_results[original_id]["enrichment_data"]
                )
                entity.is_enriched = True
                self.enriched_entities.append(entity)

        self.soar_action.update_entities(self.enriched_entities)


def main() -> NoReturn:
    ScanEntities().run()


if __name__ == "__main__":
    main()

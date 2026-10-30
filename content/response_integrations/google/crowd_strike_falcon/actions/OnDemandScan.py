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

import collections
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Dict, TYPE_CHECKING

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_comma_separated_to_list
from TIPCommon.validation import ParameterValidator

from ..core.AsyncActionBaseClass import ActionResult, AsyncActionBaseClass
from ..core import constants
from ..core.CrowdStrikeManager import CrowdStrikeManager
from ..core.CrowdStrikeParser import CrowdStrikeParser
from ..core.datamodels import OnDemandScanData
from ..core.exceptions import (
    ODSDetectionLevelError,
    ODSInvalidFilePathError,
    CrowdStrikeBadRequestError,
    InvalidCidError,
)
from ..core.utils import get_entity_original_identifier, validate_device_id

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import SingleJson


ENTITIES_MAPPER = constants.ENTITIES_MAPPER

DEFAULT_FILE_PATH_TO_SCAN = "C:\\Windows"

NameToIdMap = Dict[str, str]
NameToScanDetailMap = Dict[str, OnDemandScanData]
HostGroupIDsTuple = collections.namedtuple("HostGroupIDsTuple", ["valid_host_groups_map", "invalid_host_groups"])
HostIDsTuple = collections.namedtuple("HostIDsTuple", ["valid_hosts_map", "invalid_hosts"])
ScanMappingsTuple = collections.namedtuple("ScanMappingsTuple", ["host_group_scan_mapping", "host_scan_mapping"])
ScanDetailsTuple = collections.namedtuple("ScanDetailsTuple", ["host_group_scan_details", "host_scan_details"])


@dataclass
class ActionData:
    processed_host_group_scans: NameToScanDetailMap
    processed_host_scans: NameToScanDetailMap
    pending_host_group_scans: NameToScanDetailMap
    pending_host_scans: NameToScanDetailMap
    failed_host_group_scans: list
    failed_host_scans: list
    invalid_host_groups: list
    invalid_hosts: list


@dataclass
class ActionParams:
    file_paths_to_scan: list[str]
    file_paths_to_exclude: list[str]
    cpu_priority: int
    sensor_ml_level_detection: int
    sensor_ml_level_prevention: int
    cloud_ml_level_detection: int
    cloud_ml_level_prevention: int


@dataclass
class HostValidationData:
    valid_host_groups_map: NameToIdMap
    invalid_host_groups: list[str]
    valid_hosts_map: NameToIdMap
    invalid_hosts: list[str]
    host_scan_mapping: NameToScanDetailMap = field(default_factory=dict)
    host_group_scan_mapping: NameToScanDetailMap = field(default_factory=dict)


class OnDemandScanAction(AsyncActionBaseClass):
    def __init__(self, siemplify: SiemplifyAction) -> None:
        super().__init__(siemplify)
        self.parser = CrowdStrikeParser()
        self.results = ActionData(
            processed_host_group_scans={},
            processed_host_scans={},
            pending_host_group_scans={},
            pending_host_scans={},
            failed_host_group_scans=[],
            failed_host_scans=[],
            invalid_host_groups=[],
            invalid_hosts=[],
        )

    def _extract_action_configuration(self) -> None:
        integration_cid = self.config.customer_id
        action_cid = extract_action_param(
            siemplify=self.siemplify,
            param_name="Customer ID",
            print_value=True,
        )
        customer_id = action_cid or integration_cid
        self.params.cid = customer_id
        if self.params.cid:
            self.config.customer_id = self.params.cid

        self.params.file_paths_to_scan = extract_action_param(
            siemplify=self.siemplify,
            param_name="File Paths To Scan",
            is_mandatory=True,
            default_value=DEFAULT_FILE_PATH_TO_SCAN,
            print_value=True,
        )
        self.params.file_paths_to_exclude = extract_action_param(
            siemplify=self.siemplify,
            param_name="File Paths To Exclude From Scan",
            print_value=True,
        )
        self.params.host_group_name = extract_action_param(
            siemplify=self.siemplify, param_name="Host Group Name", print_value=True
        )
        self.params.scan_description = extract_action_param(
            siemplify=self.siemplify,
            param_name="Scan Description",
            default_value="Scan initialized by Google SecOps.",
            print_value=True,
        )
        self.params.cpu_priority = extract_action_param(
            siemplify=self.siemplify, param_name="CPU Priority", print_value=True
        )
        self.params.sensor_detection_level = extract_action_param(
            siemplify=self.siemplify,
            param_name="Sensor Anti-malware Detection Level",
            print_value=True,
        )
        self.params.sensor_prevention_level = extract_action_param(
            siemplify=self.siemplify,
            param_name="Sensor Anti-malware Prevention Level",
            print_value=True,
        )
        self.params.cloud_detection_level = extract_action_param(
            siemplify=self.siemplify,
            param_name="Cloud Anti-malware Detection Level",
            print_value=True,
        )
        self.params.cloud_prevention_level = extract_action_param(
            siemplify=self.siemplify,
            param_name="Cloud Anti-malware Prevention Level",
            print_value=True,
        )
        self.params.quarantine_hosts = extract_action_param(
            siemplify=self.siemplify,
            param_name="Quarantine Hosts",
            print_value=True,
            default_value=False,
            input_type=bool,
        )
        self.params.create_endpoint_notification = extract_action_param(
            siemplify=self.siemplify,
            param_name="Create Endpoint Notification",
            print_value=True,
            default_value=True,
            input_type=bool,
        )
        self.params.max_scan_duration = extract_action_param(
            siemplify=self.siemplify,
            param_name="Max Scan Duration",
            default_value=constants.DEFAULT_MAX_SCAN_DURATION,
            input_type=int,
            print_value=True,
        )
        self.params.hostname = extract_action_param(
            siemplify=self.siemplify,
            param_name="Hostname",
            print_value=True,
        )
        self.params.device_id = extract_action_param(
            siemplify=self.siemplify,
            param_name="Device ID",
            print_value=True,
        )
        validate_device_id(self.params.device_id)
        self.params.additional_data = extract_action_param(
            siemplify=self.siemplify, param_name="additional_data", default_value="{}"
        )

    def _validate_params(self, validator: ParameterValidator) -> None:
        validator.validate_csv(param_name="File Paths To Scan", csv_string=self.params.file_paths_to_scan)
        validator.validate_csv(
            param_name="File Paths To Exclude From Scan",
            csv_string=self.params.file_paths_to_exclude,
        )
        validator.validate_csv(param_name="Host Group Name", csv_string=self.params.host_group_name)
        validator.validate_ddl(
            param_name="CPU Priority",
            value=self.params.cpu_priority,
            ddl_values=constants.CPU_PRIORITY_MAPPING.keys(),
        )
        validator.validate_ddl(
            param_name="Sensor Anti-malware Detection Level",
            value=self.params.sensor_detection_level,
            ddl_values=constants.DETECTION_LEVEL_PARAM_VALUES,
        )
        validator.validate_ddl(
            param_name="Sensor Anti-malware Prevention Level",
            value=self.params.sensor_prevention_level,
            ddl_values=constants.PREVENTION_LEVEL_PARAM_VALUES,
        )
        validator.validate_ddl(
            param_name="Cloud Anti-malware Detection Level",
            value=self.params.cloud_detection_level,
            ddl_values=constants.DETECTION_LEVEL_PARAM_VALUES,
        )
        validator.validate_ddl(
            param_name="Cloud Anti-malware Prevention Level",
            value=self.params.cloud_prevention_level,
            ddl_values=constants.PREVENTION_LEVEL_PARAM_VALUES,
        )
        validator.validate_integer(param_name="Max Scan Duration", value=self.params.max_scan_duration)
        self.params.hostnames = validator.validate_csv(
            param_name="Hostname",
            csv_string=self.params.hostname,
        )
        self.params.device_ids = validator.validate_csv(
            param_name="Device ID",
            csv_string=self.params.device_id,
        )

        if self.params.max_scan_duration and self.params.max_scan_duration < constants.DEFAULT_MAX_SCAN_DURATION:
            raise ValueError('Please provide positive number in parameter "Max Scan Duration".')

    def _perform_action(self, manager: CrowdStrikeManager) -> ActionResult:
        action_params = self._get_action_params()

        self._validate_if_detection_level_is_higher_than_prevention_level(action_params)
        self._validate_file_paths(action_params)

        suitable_entities = self._get_and_validate_suitable_entities()

        additional_data = json.loads(self.params.additional_data)

        host_group_scan_mapping: NameToScanDetailMap = {}
        host_scan_mapping: NameToScanDetailMap = {}
        host_validation_data = HostValidationData(
            valid_host_groups_map={},
            invalid_host_groups=[],
            valid_hosts_map={},
            invalid_hosts=[],
        )

        if not additional_data:
            host_group_ids = self._get_host_group_ids(manager)
            valid_host_groups_map: NameToIdMap = host_group_ids.valid_host_groups_map
            invalid_host_groups: list[str] = host_group_ids.invalid_host_groups

            host_ids = self._get_host_ids(manager, suitable_entities, cid=self.params.cid)
            valid_hosts_map: NameToIdMap = host_ids.valid_hosts_map
            invalid_hosts: list[str] = host_ids.invalid_hosts

            scan_mappings = self._scan_host_groups_and_hosts(
                manager=manager,
                action_params=action_params,
                valid_host_groups_map=valid_host_groups_map,
                valid_hosts_map=valid_hosts_map,
            )
            host_group_scan_mapping: NameToScanDetailMap = scan_mappings.host_group_scan_mapping
            host_scan_mapping: NameToScanDetailMap = scan_mappings.host_scan_mapping

            host_validation_data = HostValidationData(
                valid_host_groups_map=valid_host_groups_map,
                invalid_host_groups=invalid_host_groups,
                valid_hosts_map=valid_hosts_map,
                invalid_hosts=invalid_hosts,
                host_scan_mapping={
                    k: v.to_json() if hasattr(v, "to_json") else v for k, v in host_scan_mapping.items()
                },
                host_group_scan_mapping={
                    k: v.to_json() if hasattr(v, "to_json") else v for k, v in host_group_scan_mapping.items()
                },
            )

            self._set_action_data(host_validation_data)

            scan_details = self._get_scan_details(manager, host_group_scan_mapping, host_scan_mapping)
            host_group_scan_details: NameToScanDetailMap = scan_details.host_group_scan_details
            host_scan_details: NameToScanDetailMap = scan_details.host_scan_details

            self._set_action_result(
                host_group_scan_details=host_group_scan_details,
                host_scan_details=host_scan_details,
                host_validation_data=host_validation_data,
            )
            self._set_json_result()
            self._log_messages()
        else:
            self.results = ActionData(**additional_data)
            scan_details = self._get_scan_details(manager, host_group_scan_mapping, host_scan_mapping)
            host_group_scan_details: NameToScanDetailMap = scan_details.host_group_scan_details
            host_scan_details: NameToScanDetailMap = scan_details.host_scan_details

            self._set_action_result(
                host_group_scan_details=host_group_scan_details,
                host_scan_details=host_scan_details,
                host_validation_data=host_validation_data,
            )
            self._set_json_result()
            self._log_messages()

        return self._finalize_action()

    def _get_action_params(self) -> ActionParams:
        file_paths_to_scan = convert_comma_separated_to_list(self.params.file_paths_to_scan)
        file_paths_to_exclude = convert_comma_separated_to_list(self.params.file_paths_to_exclude)
        cpu_priority = constants.CPU_PRIORITY_MAPPING.get(self.params.cpu_priority)
        sensor_ml_level_detection = constants.DETECTION_PREVENTION_MAPPING.get(self.params.sensor_detection_level)
        sensor_ml_level_prevention = constants.DETECTION_PREVENTION_MAPPING.get(self.params.sensor_prevention_level)
        cloud_ml_level_detection = constants.DETECTION_PREVENTION_MAPPING.get(self.params.cloud_detection_level)
        cloud_ml_level_prevention = constants.DETECTION_PREVENTION_MAPPING.get(self.params.cloud_prevention_level)

        action_params = ActionParams(
            file_paths_to_scan=file_paths_to_scan,
            file_paths_to_exclude=file_paths_to_exclude,
            cpu_priority=cpu_priority,
            sensor_ml_level_detection=sensor_ml_level_detection,
            sensor_ml_level_prevention=sensor_ml_level_prevention,
            cloud_ml_level_detection=cloud_ml_level_detection,
            cloud_ml_level_prevention=cloud_ml_level_prevention,
        )

        return action_params

    def _validate_if_detection_level_is_higher_than_prevention_level(self, action_params: ActionParams) -> bool:
        if (action_params.cloud_ml_level_detection >= action_params.cloud_ml_level_prevention) and (
            action_params.sensor_ml_level_detection >= action_params.sensor_ml_level_prevention
        ):
            return True
        raise ODSDetectionLevelError(self._detection_level_error_msg)

    def _validate_file_paths(self, action_params: ActionParams) -> bool:
        drive_letter_pattern = r"[A-Z]:\\"

        for path in action_params.file_paths_to_scan:
            is_valid = bool(re.match(drive_letter_pattern, path))
            if not is_valid:
                raise ODSInvalidFilePathError(self._invalid_file_path_schema_error_msg)

        for path in action_params.file_paths_to_exclude:
            is_valid = bool(re.match(drive_letter_pattern, path))
            if not is_valid:
                raise ODSInvalidFilePathError(self._invalid_file_path_schema_error_msg)

        return True

    def _get_and_validate_suitable_entities(self) -> dict[str, str]:
        """
        Retrieves and validates suitable entities from the target
        entities and additional hostnames.

        This function filters the target entities based on their type, matching
        them against the ENTITIES_MAPPER. It then creates a mapping of entity
        identifiers to their corresponding values from the mapper.
        Additionally, it incorporates hostnames from the instance parameters,
        mapping them to the HOSTNAME value from ENTITIES_MAPPER.

        Returns:
            dict[str, str]: A dictionary where keys are entity identifiers
            (original identifiers for target entities or hostnames from parameters),
            and values are the corresponding values from ENTITIES_MAPPER.
        """
        suitable_entities = [
            entity for entity in self.siemplify.target_entities if entity.entity_type in ENTITIES_MAPPER
        ]

        suitable_items_mapping = {
            get_entity_original_identifier(entity): entity.entity_type for entity in suitable_entities
        }
        suitable_items_mapping.update({hostname: EntityTypes.HOSTNAME for hostname in self.params.hostnames})
        suitable_items_mapping.update({device_id: "DEVICE_ID" for device_id in self.params.device_ids})

        return suitable_items_mapping

    def _get_host_group_ids(self, manager: CrowdStrikeManager) -> HostGroupIDsTuple:
        host_group_names: list[str] = convert_comma_separated_to_list(self.params.host_group_name)

        valid_host_groups_map: NameToIdMap = {}
        invalid_host_groups: list[str] = []

        if host_group_names:
            for host_group_name in host_group_names:
                host_group = manager.get_host_group_by_name(host_group_name)

                if not host_group:
                    invalid_host_groups.append(host_group_name)
                else:
                    valid_host_groups_map[host_group_name] = host_group.id

        return HostGroupIDsTuple(valid_host_groups_map, invalid_host_groups)

    def _get_host_ids(
        self,
        manager: CrowdStrikeManager,
        suitable_entities: dict[str, str],
        cid: str | None = None,
    ) -> HostIDsTuple:
        valid_hosts_map: NameToIdMap = {}
        invalid_hosts: list[str] = []

        for entity_identifier, entity_type in suitable_entities.items():
            try:
                if entity_type == "DEVICE_ID":
                    device_info = manager.get_devices(devices_ids=[entity_identifier])
                    devices = [entity_identifier] if device_info else []
                else:
                    request_filter = {key: entity_identifier for key in ENTITIES_MAPPER[entity_type]}
                    request_filter["cid"] = cid
                    request_filter["platform_name"] = "Windows"
                    devices = manager.search_device_ids(**request_filter)

            except CrowdStrikeBadRequestError as err:
                if constants.CID_ERROR in str(err).lower():
                    raise InvalidCidError("Incorrect Customer ID specified.") from err
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.siemplify.LOGGER.error(f"Failed to search device for: {entity_identifier}.")
                self.siemplify.LOGGER.exception(e)
                devices = []

            if not devices:
                invalid_hosts.append(entity_identifier)
            else:
                existing_entity = next((k for k, v in valid_hosts_map.items() if v == devices[0]), None)
                if existing_entity:
                    self.siemplify.LOGGER.info(
                        f"Identifier '{entity_identifier}' maps to device ID '{devices[0]}', which is already "
                        f"associated with entity '{existing_entity}'. Skipping duplication."
                    )
                    continue
                valid_hosts_map[entity_identifier] = devices[0]

        return HostIDsTuple(valid_hosts_map, invalid_hosts)

    def _get_scan_details(
        self,
        manager: CrowdStrikeManager,
        host_group_scan_mapping: NameToScanDetailMap,
        host_scan_mapping: NameToScanDetailMap,
    ) -> ScanDetailsTuple:
        host_group_scan_details: NameToScanDetailMap = {}
        host_scan_details: NameToScanDetailMap = {}

        additional_data = json.loads(self.params.additional_data)

        if additional_data:
            host_group_scan_mapping = self.results.pending_host_group_scans
            host_scan_mapping = self.results.pending_host_scans

        for host_group_name, host_group_scan_detail in host_group_scan_mapping.items():
            if isinstance(host_group_scan_detail, dict):
                host_group_scan_detail = self.parser.build_on_demand_scan_data(host_group_scan_detail)
            scan_detail = manager.get_on_demand_scan_details(scan_id=host_group_scan_detail.scan_id)
            host_group_scan_details[host_group_name] = scan_detail if scan_detail.resources else host_group_scan_detail

        for host_name, host_scan_detail in host_scan_mapping.items():
            if isinstance(host_scan_detail, dict):
                host_scan_detail = self.parser.build_on_demand_scan_data(host_scan_detail)
            scan_detail = manager.get_on_demand_scan_details(scan_id=host_scan_detail.scan_id)
            host_scan_details[host_name] = scan_detail if scan_detail.resources else host_scan_detail

        return ScanDetailsTuple(host_group_scan_details, host_scan_details)

    def _scan_host_group_ids(
        self,
        manager: CrowdStrikeManager,
        action_params: ActionParams,
        valid_host_groups_map: NameToIdMap,
    ) -> NameToScanDetailMap:
        scan_mapping: NameToScanDetailMap = {}

        for host_group_name, host_group_id in valid_host_groups_map.items():
            existing_scan = self._find_existing_scan_for_host_group(
                manager=manager,
                host_group_id=host_group_id,
                action_params=action_params,
            )
            if existing_scan is not None:
                self.siemplify.LOGGER.info(
                    f"Host group '{host_group_name}' already has an active scan "
                    f"({existing_scan.scan_id}). Subscribing..."
                )
                scan_mapping[host_group_name] = existing_scan
                continue

            scan_detail = manager.start_on_demand_scan(
                host_group_id=host_group_id,
                file_paths_to_scan=action_params.file_paths_to_scan,
                file_paths_to_exclude=action_params.file_paths_to_exclude,
                cpu_priority=action_params.cpu_priority,
                description=self.params.scan_description,
                quarantine_hosts=self.params.quarantine_hosts,
                endpoint_notification=self.params.create_endpoint_notification,
                sensor_ml_level_detection=action_params.sensor_ml_level_detection,
                sensor_ml_level_prevention=action_params.sensor_ml_level_prevention,
                cloud_ml_level_detection=action_params.cloud_ml_level_detection,
                cloud_ml_level_prevention=action_params.cloud_ml_level_prevention,
                max_scan_duration=self.params.max_scan_duration,
            )

            scan_mapping[host_group_name] = scan_detail

        return scan_mapping

    def _scan_host_ids(
        self,
        manager: CrowdStrikeManager,
        action_params: ActionParams,
        valid_hosts_map: NameToIdMap,
    ) -> NameToScanDetailMap:
        scan_mapping: NameToScanDetailMap = {}

        for host_name, host_id in valid_hosts_map.items():
            existing_scan = self._find_existing_scan_for_host(
                manager=manager,
                host_id=host_id,
                action_params=action_params,
            )
            if existing_scan is not None:
                self.siemplify.LOGGER.info(
                    f"Host '{host_name}' already has an active scan ({existing_scan.scan_id}). Subscribing..."
                )
                scan_mapping[host_name] = existing_scan
                continue

            scan_detail = manager.start_on_demand_scan(
                host_id=host_id,
                file_paths_to_scan=action_params.file_paths_to_scan,
                file_paths_to_exclude=action_params.file_paths_to_exclude,
                cpu_priority=action_params.cpu_priority,
                description=self.params.scan_description,
                quarantine_hosts=self.params.quarantine_hosts,
                endpoint_notification=self.params.create_endpoint_notification,
                sensor_ml_level_detection=action_params.sensor_ml_level_detection,
                sensor_ml_level_prevention=action_params.sensor_ml_level_prevention,
                cloud_ml_level_detection=action_params.cloud_ml_level_detection,
                cloud_ml_level_prevention=action_params.cloud_ml_level_prevention,
                max_scan_duration=self.params.max_scan_duration,
            )

            scan_mapping[host_name] = scan_detail

        return scan_mapping

    def _find_existing_scan_for_host(
        self,
        manager: CrowdStrikeManager,
        host_id: str,
        action_params: ActionParams,
    ) -> OnDemandScanData | None:
        return self._find_existing_scan(
            manager=manager,
            entity_id=host_id,
            entity_attribute="hosts",
            action_params=action_params,
        )

    def _find_existing_scan_for_host_group(
        self,
        manager: CrowdStrikeManager,
        host_group_id: str,
        action_params: ActionParams,
    ) -> OnDemandScanData | None:
        return self._find_existing_scan(
            manager=manager,
            entity_id=host_group_id,
            entity_attribute="host_groups",
            action_params=action_params,
        )

    def _find_existing_scan(
        self,
        manager: CrowdStrikeManager,
        entity_id: str,
        entity_attribute: str,
        action_params: ActionParams,
    ) -> OnDemandScanData | None:
        """Generic method to check if an active scan exists for the given host or host
        group with the same configuration.

        Args:
            manager: CrowdStrikeManager instance.
            entity_id(str): host ID or host group ID
            entity_attribute(str): "hosts" or "host_groups"
            action_params(ActionParams): action parameters.

        Returns:
            OnDemandScanData | None: matching scan if exists.
        """

        def _is_matching_scan(scan: OnDemandScanData) -> bool:
            """Check whether a scan matches the action parameters."""
            return all([
                set(scan.file_paths) == set(action_params.file_paths_to_scan),
                set(scan.scan_exclusions) == set(action_params.file_paths_to_exclude),
                scan.cpu_priority == action_params.cpu_priority,
                scan.cloud_ml_detection_level == action_params.cloud_ml_level_detection,
                scan.cloud_ml_prevention_level == action_params.cloud_ml_level_prevention,
                scan.sensor_ml_detection_level == action_params.sensor_ml_level_detection,
                scan.sensor_ml_prevention_level == action_params.sensor_ml_level_prevention,
                scan.description == self.params.scan_description,
                scan.quarantine == self.params.quarantine_hosts,
                scan.max_duration == self.params.max_scan_duration,
                scan.endpoint_notification == self.params.create_endpoint_notification,
            ])

        since_time: str = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        active_scan_ids = manager.get_active_scan_ids(since_time=since_time)

        for scan_id in active_scan_ids:
            scan = manager.get_on_demand_scan_details(scan_id)

            if not hasattr(scan, entity_attribute):
                continue

            if entity_id not in getattr(scan, entity_attribute, []):
                continue

            if _is_matching_scan(scan):
                return scan

        return None

    def _scan_host_groups_and_hosts(
        self,
        manager: CrowdStrikeManager,
        action_params: ActionParams,
        valid_host_groups_map: NameToIdMap,
        valid_hosts_map: NameToIdMap,
    ) -> ScanMappingsTuple:
        host_group_scan_mapping: NameToScanDetailMap = {}
        host_scan_mapping: NameToScanDetailMap = {}

        if valid_host_groups_map:
            host_group_scan_mapping = self._scan_host_group_ids(manager, action_params, valid_host_groups_map)

        if valid_hosts_map:
            host_scan_mapping = self._scan_host_ids(manager, action_params, valid_hosts_map)

        return ScanMappingsTuple(host_group_scan_mapping, host_scan_mapping)

    def _set_action_data(self, host_validation_data: HostValidationData) -> None:
        """Set scans data into the results attribute. if it's first run set all
            scans to pending_scans in result attribute otherwise
            additional data from async run.

        Args:
            host_validation_data (HostValidationData): host info.
        """
        additional_data = json.loads(self.params.additional_data)

        self.results.invalid_hosts = host_validation_data.invalid_hosts

        self.results.invalid_host_groups = host_validation_data.invalid_host_groups

        if not additional_data:  # first-run
            self.results.pending_host_scans = host_validation_data.host_scan_mapping
            self.results.pending_host_group_scans = host_validation_data.host_group_scan_mapping
        else:
            self.results = ActionData(**additional_data)

    def _set_action_result(
        self,
        host_group_scan_details: NameToScanDetailMap,
        host_scan_details: NameToScanDetailMap,
        host_validation_data: HostValidationData,
    ) -> None:
        """Set the result of pending, processed and failed On-Demand Scans.

        Args:
            src_mailboxes (utils.MailboxResult): The result of processing mailboxes with
                source folder.
            dst_mailboxes (utils.MailboxResult): The result of processing mailboxes with
                destination folder.
            emails (list[MicrosoftGraphEmail]): List of moved emails.
        """
        if host_validation_data.invalid_host_groups:
            self.results.invalid_host_groups = host_validation_data.invalid_host_groups
        if host_validation_data.invalid_hosts:
            self.results.invalid_hosts = host_validation_data.invalid_hosts

        for host_name, scan_details in host_group_scan_details.items():
            status = scan_details.status.lower() if isinstance(scan_details.status, str) else scan_details.status
            if status == constants.ScanStatus.COMPLETED.value:
                self.results.pending_host_group_scans.pop(host_name, None)
                if host_name in self.results.failed_host_group_scans:
                    self.results.failed_host_group_scans.remove(host_name)
                self.results.processed_host_group_scans[host_name] = scan_details.to_json()
            elif status in (
                constants.ScanStatus.CANCELED.value,
                constants.ScanStatus.FAILED.value,
            ):
                self.results.processed_host_group_scans.pop(host_name, None)
                self.results.pending_host_group_scans.pop(host_name, None)
                if host_name not in self.results.failed_host_group_scans:
                    self.results.failed_host_group_scans.append(host_name)
            else:
                self.results.processed_host_group_scans.pop(host_name, None)
                if host_name in self.results.failed_host_group_scans:
                    self.results.failed_host_group_scans.remove(host_name)
                self.results.pending_host_group_scans[host_name] = scan_details.to_json()

        for host_name, scan_details in host_scan_details.items():
            status = scan_details.status.lower() if isinstance(scan_details.status, str) else scan_details.status
            if status == constants.ScanStatus.COMPLETED.value:
                self.results.pending_host_scans.pop(host_name, None)
                if host_name in self.results.failed_host_scans:
                    self.results.failed_host_scans.remove(host_name)
                self.results.processed_host_scans[host_name] = scan_details.to_json()
            elif status in (
                constants.ScanStatus.CANCELED.value,
                constants.ScanStatus.FAILED.value,
            ):
                self.results.processed_host_scans.pop(host_name, None)
                self.results.pending_host_scans.pop(host_name, None)
                if host_name not in self.results.failed_host_scans:
                    self.results.failed_host_scans.append(host_name)
            else:
                self.results.processed_host_scans.pop(host_name, None)
                if host_name in self.results.failed_host_scans:
                    self.results.failed_host_scans.remove(host_name)
                self.results.pending_host_scans[host_name] = scan_details.to_json()

    def _set_json_result(self) -> None:
        """Add json result to the case."""
        json_result_scans = []

        def process_scan_details(scan_details: SingleJson) -> SingleJson:
            if isinstance(scan_details, dict):
                scan_details = self.parser.build_on_demand_scan_data(scan_details)
            return self._rename_scan_inclusions(scan_details.resources)

        for host_name, scan_details in self.results.processed_host_group_scans.items():
            resources = process_scan_details(scan_details)
            json_result_scans.append({"Entity": host_name, "EntityResult": resources})

        for host_name, scan_details in self.results.processed_host_scans.items():
            resources = process_scan_details(scan_details)
            json_result_scans.append({"Entity": host_name, "EntityResult": resources})

        if json_result_scans:
            self.siemplify.result.add_result_json(json_result_scans)

    def _rename_scan_inclusions(
        self,
        resources: list[SingleJson],
    ) -> list[SingleJson]:
        """Rename 'scan_inclusions' key to 'file_paths' in each resource dict.

        Args:
            resources (list[SingleJson]): list of resources.

        Returns:
            list[SingleJson]: list of updated resources.
        """
        updated_resources = []
        for resource in resources:
            if "scan_inclusions" in resource:
                resource["file_paths"] = resource.pop("scan_inclusions")
            updated_resources.append(resource)

        return updated_resources

    def _log_messages(self) -> None:
        if self.results.failed_host_group_scans and not self.results.processed_host_group_scans:
            self.logger.error(self._all_invalid_host_groups_err_msg)

        if self.results.failed_host_scans and not self.results.processed_host_scans:
            self.logger.error(self._all_invalid_hosts_err_msg)

        if self.results.failed_host_group_scans and self.results.processed_host_group_scans:
            self.logger.error(self._some_invalid_host_groups_err_msg)

        if self.results.failed_host_scans and self.results.processed_host_scans:
            self.logger.error(self._some_invalid_hosts_err_msg)

    def _finalize_action(self) -> ActionResult:
        if self._is_timeout():
            return self._finalize_action_on_timeout()

        if self.results.pending_host_group_scans or self.results.pending_host_scans:
            return self._finalize_action_on_inprogress()

        if (
            self.results.failed_host_group_scans
            or self.results.failed_host_scans
            or self.results.invalid_host_groups
            or self.results.invalid_hosts
            or not (self.results.processed_host_scans or self.results.processed_host_group_scans)
        ):
            return self._finalize_action_on_failure()
        return self._finalize_action_on_success()

    def _finalize_action_on_timeout(self) -> ActionResult:
        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_inprogress(self) -> ActionResult:
        self.output_messages.append(self._in_progress_msg)

        return ActionResult(ExecutionState.IN_PROGRESS, json.dumps(asdict(self.results)))

    def _finalize_action_on_failure(self) -> ActionResult:
        if self.results.processed_host_scans or self.results.processed_host_group_scans:
            self._finalize_action_on_success()
            # case: some success and some invalid + failed hosts
            if self.results.invalid_hosts or self.results.failed_host_scans:
                self.output_messages.append(self._some_invalid_hosts_err_msg)

            # case: some success and some invalid + failed host groups
            if self.results.invalid_host_groups or self.results.failed_host_group_scans:
                self.output_messages.append(self._some_invalid_host_groups_err_msg)

            return ActionResult(ExecutionState.COMPLETED, True)

        else:
            # case: no success and all invalid + failed hosts
            if self.results.invalid_hosts or self.results.failed_host_scans:
                self.output_messages.append(self._all_invalid_hosts_err_msg)

            # case: no success and all invalid + failed host groups
            if self.results.invalid_host_groups or self.results.failed_host_group_scans:
                self.output_messages.append(self._all_invalid_host_groups_err_msg)

            if not (
                self.results.invalid_hosts
                or self.results.failed_host_scans
                or self.results.invalid_host_groups
                or self.results.failed_host_group_scans
            ):
                self.output_messages.append(self._all_invalid_hosts_err_msg)

            return ActionResult(ExecutionState.COMPLETED, False)

    def _finalize_action_on_success(self) -> ActionResult:
        if self.results.processed_host_scans:
            self.output_messages.append(self._success_host_scans_msg)
        if self.results.processed_host_group_scans:
            self.output_messages.append(self._success_host_group_scans_msg)

        return ActionResult(ExecutionState.COMPLETED, True)

    @property
    def _success_host_scans_msg(self) -> str:
        entities_csv = ", ".join(entities for entities in self.results.processed_host_scans.keys())

        message = f"Successfully scanned and returned results for the following hosts in Crowdstrike: {entities_csv}"

        return message

    @property
    def _some_invalid_hosts_err_msg(self) -> str:
        failed_entities = self.results.invalid_hosts + self.results.failed_host_scans
        failed_entities = list(set(failed_entities))
        entities_csv = ", ".join(entitiy for entitiy in failed_entities)

        message = (
            "Action couldn't start a scan on the following hosts in Crowdstrike: "
            f"{entities_csv}. "
            "They are either not found or non-Windows instances."
        )

        return message

    @property
    def _all_invalid_hosts_err_msg(self) -> str:
        return (
            "None of the provided hosts were found or "
            "none of the hosts were Windows instances. "
            "No scans have been created."
        )

    @property
    def _success_host_group_scans_msg(self) -> str:
        entities_csv = ", ".join(entities for entities in self.results.processed_host_group_scans.keys())
        message = (
            f"Successfully scanned and returned results for the following host groups in Crowdstrike: {entities_csv}"
        )

        return message

    @property
    def _some_invalid_host_groups_err_msg(self) -> str:
        failed_entities = self.results.invalid_host_groups + self.results.failed_host_group_scans
        failed_entities = list(set(failed_entities))
        entities_csv = ", ".join(entitiy for entitiy in failed_entities)

        message = f"The following host groups were not found in Crowdstrike: {entities_csv}"

        return message

    @property
    def _all_invalid_host_groups_err_msg(self) -> str:
        return "None of the provided host groups were found in CrowdStrike."

    @property
    def _in_progress_msg(self) -> str:
        message = "Waiting for scan results for the following entities or host groups: "

        in_progress_host_groups = list(self.results.pending_host_group_scans.keys())
        in_progress_hosts = list(self.results.pending_host_scans.keys())
        in_progress_entities = in_progress_host_groups + in_progress_hosts
        in_progress_entities_csv = ", ".join(entity for entity in in_progress_entities)

        message += in_progress_entities_csv

        return message

    @property
    def _detection_level_error_msg(self) -> str:
        return (
            'Error executing action "On-Demand Scan". '
            "Reason: Detection level should be equal to or "
            "higher than the Prevention level. "
            "Please check the corresponding parameters."
        )

    @property
    def _invalid_file_path_schema_error_msg(self) -> str:
        return (
            'Error executing action "On-Demand Scan". '
            'Reason: Invalid value provided in the parameter "File Path to Scan" or '
            '"File Paths To Exclude From Scan" Please check the spelling, '
            "it should reflect the Windows file path structure."
        )


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.ON_DEMAND_SCAN_SCRIPT_NAME
    action = OnDemandScanAction(siemplify)
    action.run()


if __name__ == "__main__":
    main()

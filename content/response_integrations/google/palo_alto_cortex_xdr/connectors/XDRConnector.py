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

import copy
import datetime
import hashlib
import json
import os
import sys
from typing import TYPE_CHECKING, Callable, TypeVar

import requests
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    dict_to_flat,
    unix_now,
    utc_now,
)

from EnvironmentCommon import GetEnvironmentCommonFactory
from TIPCommon.base.connector import Connector
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run
from TIPCommon.validation import ParameterValidator
from ..core import constants
from ..core.auth import AuthenticatedSession
from ..core.datamodels import (
    Alert,
    FileArtifact,
    IncidentExtraData,
    IncidentInfo,
    NetworkArtifact,
)
from ..core.exceptions import PaloAltoXdrValidationError, XDRException
from ..core.utils import get_integration_parameters
from ..core.XDRManager import ApiParameters, XDRManager

if TYPE_CHECKING:
    from ..core.datamodels import IntegrationParameters

SEVERITY_RANK: dict[str, int] = {
    sev: i for i, sev in enumerate(constants.SEVERITY_ORDER)
}
# pylint: disable=invalid-name
T_Artifact = TypeVar("T_Artifact", FileArtifact, NetworkArtifact)
invalid_sev_rank: int = constants.INVALID_SEVERITY_RANK


class CaseProcessor:

    def __init__(self, connector: "XDRConnector"):
        self.connector = connector
        self.siemplify = connector.siemplify
        self.logger = connector.logger
        self.params = connector.params
        self.context = connector.context
        self.manager = connector.manager
        self.environment_common = connector.environment_common

    def process_single_incident(
        self,
        incident: IncidentInfo,
    ) -> tuple[list[CaseInfo], list[str]]:
        """
        Process a single incident, either as one case or split into multiple cases
        based on alerts.
        """
        try:
            if self.params.split_incident_alerts:
                return self._process_incident_by_splitting(incident)

            return self._process_incident_as_single_case(incident)

        except (
            requests.exceptions.RequestException,
            PaloAltoXdrValidationError,
            XDRException,
        ) as e:
            incident_id: str = incident.incident_id or constants.UNKNOWN_INCIDENT_ID
            self.logger.error(f"Failed to process incident {incident_id}: {e}")
            self.logger.exception(e)
            self.context.failed_incident_ids.append(incident_id)
            return [], []

    def _generate_incident_version_id(
        self,
        incident_id: str,
        alert_ids: list[str],
    ) -> str:
        id_string = f"{incident_id}{''.join(sorted(alert_ids))}"
        return hashlib.sha256(id_string.encode()).hexdigest()

    def _process_incident_as_single_case(
        self,
        incident: IncidentInfo,
    ) -> tuple[list[CaseInfo], list[str]]:
        extra_data: IncidentExtraData | None = self._get_and_validate_incident_alerts(
            incident,
        )

        if not extra_data:
            processed_ids: list[str] = self._handle_incident_with_no_alerts(incident)
            return [], processed_ids

        extra_data = self._filter_incident_data_by_dynamic_list(extra_data)

        if not extra_data.alerts:
            processed_ids: list[str] = self._handle_incident_with_no_alerts(incident)
            return [], processed_ids

        (
            extra_data_for_case,
            processed_ids_for_context,
        ) = self._prepare_case_data_for_incident(incident, extra_data)

        if not extra_data_for_case or not processed_ids_for_context:
            return [], []

        return self._build_and_filter_case(
            incident,
            extra_data_for_case,
            processed_ids_for_context,
        )

    def _filter_incident_data_by_dynamic_list(
        self,
        extra_data: IncidentExtraData,
    ) -> IncidentExtraData:
        original_alert_count: int = len(extra_data.alerts)
        filtered_alerts: list[Alert] = self._filter_alerts_by_dynamic_list(
            extra_data.alerts,
        )
        extra_data.alerts = filtered_alerts

        if len(filtered_alerts) < original_alert_count:
            self.logger.info(
                f"Filtered alerts by dynamic list for incident "
                f"{extra_data.incident.incident_id}. Kept {len(filtered_alerts)} "
                f"out of {original_alert_count} alerts."
            )
            (
                file_artifacts,
                network_artifacts,
            ) = self._get_artifacts_for_alerts(
                alerts=filtered_alerts,
                all_file_artifacts=extra_data.file_artifacts,
                all_network_artifacts=extra_data.network_artifacts,
            )
            extra_data.file_artifacts = file_artifacts
            extra_data.network_artifacts = network_artifacts
            self.logger.info(
                "Artifact lists have been filtered to match the remaining alerts."
            )

        return extra_data

    def _prepare_case_data_for_incident(
        self,
        incident: IncidentInfo,
        extra_data: IncidentExtraData,
    ) -> tuple[IncidentExtraData | None, list[str] | None]:
        if self.params.include_historical_artifacts:
            return self._prepare_historical_case_data(incident, extra_data)

        return self._prepare_new_alerts_case_data(incident, extra_data)

    def _get_artifacts_for_alerts(
        self,
        alerts: list[Alert],
        all_file_artifacts: list[FileArtifact],
        all_network_artifacts: list[NetworkArtifact],
    ) -> tuple[list[FileArtifact], list[NetworkArtifact]]:
        linked_files: list[FileArtifact] = self._get_linked_file_artifacts(
            alerts, all_file_artifacts
        )
        linked_network: list[NetworkArtifact] = self._get_linked_network_artifacts(
            alerts, all_network_artifacts
        )
        return linked_files, linked_network

    def _get_linked_file_artifacts(
        self,
        alerts: list[Alert],
        all_file_artifacts: list[FileArtifact],
    ) -> list[FileArtifact]:
        linked_files: list[FileArtifact] = []
        processed_hashes: set[str] = set()
        alert_sha256s: set[str] = {
            sha
            for alert in alerts
            if (sha := alert.raw_data.get(constants.ACTION_FILE_SHA256_KEY))
        }

        if not alert_sha256s:
            return []

        for artifact in all_file_artifacts:
            file_hash: str | None = artifact.raw_data.get(constants.FILE_SHA256_KEY)
            if (
                file_hash
                and file_hash in alert_sha256s
                and file_hash not in processed_hashes
            ):
                linked_files.append(artifact)
                processed_hashes.add(file_hash)

        return linked_files

    def _get_linked_network_artifacts(
        self,
        alerts: list[Alert],
        all_network_artifacts: list[NetworkArtifact],
    ) -> list[NetworkArtifact]:
        linked_network: list[NetworkArtifact] = []
        processed_ips: set[str] = set()
        alert_remote_ips: set[str] = {
            ip
            for alert in alerts
            if (ip := alert.raw_data.get(constants.ACTION_REMOTE_IP_KEY))
        }

        if not alert_remote_ips:
            return []

        for artifact in all_network_artifacts:
            remote_ip: str | None = artifact.raw_data.get(
                constants.NETWORK_REMOTE_IP_KEY
            )
            if (
                remote_ip
                and remote_ip in alert_remote_ips
                and remote_ip not in processed_ips
            ):
                linked_network.append(artifact)
                processed_ips.add(remote_ip)

        return linked_network

    def _handle_incident_with_no_alerts(
        self,
        incident: IncidentInfo,
    ) -> list[str]:
        version_id: str = self._generate_incident_version_id(
            incident.incident_id,
            [],
        )
        if version_id in self.context.existing_ids:
            self.logger.info(
                f"Incident {incident.incident_id} with no processable alerts was "
                "already processed. Skipping."
            )
            return []

        self.logger.info(
            f"Incident {incident.incident_id} contains no alerts that pass the "
            f"filters. Skipping and recording version {version_id}."
        )

        return [version_id]

    def _prepare_historical_case_data(
        self,
        incident: IncidentInfo,
        extra_data: IncidentExtraData,
    ) -> tuple[IncidentExtraData | None, list[str] | None]:
        self.logger.info(
            "Processing all alerts based on 'Include Historical Artifacts'."
        )
        alerts_to_process: list[Alert] = extra_data.alerts
        alert_ids: list[str] = [alert.alert_id for alert in alerts_to_process]
        version_id: str = self._generate_incident_version_id(
            incident.incident_id,
            alert_ids,
        )

        if version_id in self.context.existing_ids:
            self.logger.info(
                f"Incident version {version_id} (from incident "
                f"{incident.incident_id}) was already processed. Skipping."
            )
            return None, None

        processed_ids_for_context: list[str] = [version_id]
        return extra_data, processed_ids_for_context

    def _prepare_new_alerts_case_data(
        self,
        incident: IncidentInfo,
        extra_data: IncidentExtraData,
    ) -> tuple[IncidentExtraData | None, list[str] | None]:
        self.logger.info("Filtering for new alerts to prevent duplication.")
        alerts_to_process: list[Alert] = self._filter_new_alerts(
            incident.incident_id,
            extra_data.alerts,
        )

        if not alerts_to_process:
            self.logger.info(
                f"No new alerts found for incident {incident.incident_id}. Skipping."
            )
            return None, None

        processed_ids_for_context: list[str] = [
            f"{incident.incident_id}_{alert.alert_id}"
            for alert in alerts_to_process
        ]
        extra_data_for_case: IncidentExtraData = copy.deepcopy(extra_data)
        extra_data_for_case.alerts = alerts_to_process

        return extra_data_for_case, processed_ids_for_context

    def _build_and_filter_case(
        self,
        incident: IncidentInfo,
        extra_data_for_case: IncidentExtraData,
        processed_ids_for_context: list[str],
    ) -> tuple[list[CaseInfo], list[str]]:
        alerts_to_process: list[Alert] = extra_data_for_case.alerts
        self.logger.info(
            f"Found {len(alerts_to_process)} alerts to process for incident "
            f"{incident.incident_id}."
        )

        alert_ids_for_case: list[str] = [
            alert.alert_id for alert in alerts_to_process
        ]
        version_id_for_case: str = self._generate_incident_version_id(
            incident.incident_id,
            alert_ids_for_case,
        )

        full_case: CaseInfo
        _whitelist_values: list[str]
        full_case, _whitelist_values = self._create_case_from_incident(
            incident,
            extra_data_for_case,
            version_id_for_case,
        )

        if self.connector.is_overflow_alert(full_case):
            self.logger.info(
                f"Incident {full_case.ticket_id} is an overflow. Skipping."
            )
            return [], []

        return [full_case], processed_ids_for_context

    def _filter_new_alerts(
        self,
        incident_id: str,
        all_alerts: list[Alert],
    ) -> list[Alert]:
        new_alerts: list[Alert] = []
        for alert in all_alerts:
            composite_id: str = f"{incident_id}_{alert.alert_id}"
            if composite_id not in self.context.existing_ids:
                new_alerts.append(alert)

        return new_alerts

    def _process_incident_by_splitting(
        self,
        incident: IncidentInfo,
    ) -> tuple[list[CaseInfo], list[str]]:
        cases: list[CaseInfo] = []
        processed_ids: list[str] = []
        incident_id: str = incident.incident_id

        extra_data: IncidentExtraData
        alerts: list[Alert]
        threshold: int
        extra_data, alerts, threshold = self._prepare_for_splitting(incident_id)

        alert: Alert
        for alert in alerts:
            case: CaseInfo | None
            processed_id: str | None
            case, processed_id = self._process_split_alert(
                alert, incident, extra_data, threshold
            )

            if processed_id:
                processed_ids.append(processed_id)
            if case:
                cases.append(case)

        return cases, processed_ids

    def _prepare_for_splitting(
        self,
        incident_id: str,
    ) -> tuple[IncidentExtraData, list[Alert], int]:
        self.logger.info(
            f"Fetching extra data for incident {incident_id} to split alerts."
        )
        extra_data: IncidentExtraData = self.manager.get_extra_incident_data(
            incident_id,
        )
        alerts: list[Alert] = extra_data.alerts

        alert_severity_threshold: int = invalid_sev_rank
        if self.params.lowest_alert_severity_to_fetch:
            alert_severity_threshold = SEVERITY_RANK.get(
                self.params.lowest_alert_severity_to_fetch.lower(),
                invalid_sev_rank,
            )

        return extra_data, alerts, alert_severity_threshold

    def _process_split_alert(
        self,
        alert: Alert,
        incident: IncidentInfo,
        extra_data: IncidentExtraData,
        severity_threshold: int,
    ) -> tuple[CaseInfo | None, str | None]:
        alert_id: str = alert.alert_id
        composite_id = f"{incident.incident_id}_{alert_id}"

        bypass_severity_filter: bool = self._determine_severity_bypass_for_alert(
            incident,
            alert,
        )

        if self._is_alert_duplicate_or_low_severity(
            alert,
            composite_id,
            severity_threshold,
            bypass_severity_filter,
        ):
            return None, None

        case, whitelist_value = self._create_case_from_alert(
            incident,
            alert,
            extra_data,
        )

        if self._should_skip_by_dynamic_list(whitelist_value):
            return None, None

        if self.connector.is_overflow_alert(case):
            self.logger.info(f"Alert {composite_id} is an overflow. Skipping.")
            return None, None

        return case, composite_id

    def _is_alert_duplicate_or_low_severity(
        self,
        alert: Alert,
        composite_id: str,
        severity_threshold: int,
        bypass_severity_filter: bool = False,
    ) -> bool:
        if composite_id in self.context.existing_ids:
            self.logger.info(f"Alert {composite_id} was already processed. Skipping.")
            return True

        if not bypass_severity_filter and severity_threshold != invalid_sev_rank:
            alert_severity: str = alert.severity.lower()
            alert_severity_index: int = SEVERITY_RANK.get(
                alert_severity,
                invalid_sev_rank,
            )

            if alert_severity_index < severity_threshold:
                self.logger.info(
                    f"Alert {composite_id} has severity '{alert_severity}', "
                    "which is below the threshold. Skipping."
                )
                return True

        return False

    def _create_case_from_incident(
        self,
        incident: IncidentInfo,
        extra_data: IncidentExtraData,
        version_id: str,
    ) -> tuple[CaseInfo, list[str]]:
        incident_info: IncidentInfo = extra_data.incident

        rule_generator, whitelist_values = self._get_incident_case_values(
            incident.incident_id, extra_data
        )

        case: CaseInfo = self._build_incident_case_info(
            incident_info, extra_data, rule_generator, version_id
        )

        return case, whitelist_values

    def _get_incident_case_values(
        self,
        incident_id: str,
        extra_data: IncidentExtraData,
    ) -> tuple[str, list[str]]:
        fallback_value: str = extra_data.incident.description or constants.DEFAULT_NAME
        rule_generator_value: str = fallback_value

        incident_raw_data: SingleJson = getattr(extra_data.incident, "raw_data", {})
        whitelist_values: list[str] = incident_raw_data.get("incident_sources", [])

        if extra_data.alerts:
            try:
                highest_severity_alert: Alert = max(
                    extra_data.alerts,
                    key=lambda alert: SEVERITY_RANK.get(
                        alert.severity.lower(),
                        invalid_sev_rank,
                    ),
                )
                rule_generator_value = highest_severity_alert.raw_data.get(
                    constants.API_NAME_KEY, fallback_value
                )
            except (ValueError, IndexError):
                self.logger.info(
                    f"Could not determine highest severity alert for incident "
                    f"{incident_id}. Falling back to incident description."
                )

        return rule_generator_value, whitelist_values

    def _build_incident_case_info(
        self,
        incident_info: IncidentInfo,
        extra_data: IncidentExtraData,
        rule_generator: str,
        version_id: str,
    ) -> CaseInfo:
        case: CaseInfo = CaseInfo()
        case.name = incident_info.description or constants.DEFAULT_NAME
        case.ticket_id = incident_info.incident_id
        case.display_id = version_id
        case.identifier = version_id
        case.source_grouping_identifier = incident_info.incident_id
        case.device_vendor = constants.VENDOR
        case.device_product = constants.PRODUCT
        case.priority = self.connector.get_priority(incident_info.severity)
        case.start_time = incident_info.creation_time or 1
        case.end_time = incident_info.modification_time or 1
        case.events = self._get_events(extra_data)
        case.rule_generator = rule_generator
        case.environment = (
            self.environment_common.get_environment(incident_info.to_json())
            or self.siemplify.context.connector_info.environment
        )

        return case

    def _create_case_from_alert(
        self,
        incident: IncidentInfo,
        alert: Alert,
        extra_data: IncidentExtraData,
    ) -> tuple[CaseInfo, str]:
        incident_id: str = incident.incident_id
        alert_id: str = alert.alert_id
        composite_id = f"{incident_id}_{alert_id}"

        case: CaseInfo = CaseInfo()
        case.name = alert.raw_data.get(constants.API_NAME_KEY, constants.DEFAULT_NAME)
        case.ticket_id = composite_id
        case.display_id = str(composite_id)
        case.identifier = str(composite_id)
        case.source_grouping_identifier = str(incident_id)
        case.device_vendor = constants.VENDOR
        case.device_product = constants.PRODUCT
        case.priority = self.connector.get_priority(alert.severity)
        case.start_time = alert.raw_data.get(constants.API_DETECTION_TIMESTAMP_KEY, 1)
        case.end_time = alert.raw_data.get(constants.API_DETECTION_TIMESTAMP_KEY, 1)
        case.events = self._get_events(extra_data, main_alert=alert)
        case.rule_generator = case.name
        case.environment = (
            self.environment_common.get_environment(incident.to_json())
            or self.siemplify.context.connector_info.environment
        )

        whitelist_value: str = alert.raw_data.get(constants.API_SOURCE_KEY, case.name)

        return case, whitelist_value

    def _get_events(
        self,
        incident_extra_data: IncidentExtraData,
        main_alert: Alert | None = None,
    ) -> list[SingleJson]:
        events: list[SingleJson] = []
        incident: IncidentInfo = incident_extra_data.incident

        events.append(self._create_incident_event(incident))
        events.extend(self._create_alert_events(incident_extra_data, main_alert))

        is_splitting_alerts: bool = main_alert is not None

        if not is_splitting_alerts and self.params.include_historical_artifacts:
            self.logger.info(
                "Including all historical artifacts for the incident as per connector "
                "parameter."
            )
            events.extend(self._create_all_artifact_events(incident_extra_data))
        else:
            self.logger.info(
                "Including only artifacts linked to the current alert(s) to prevent "
                "duplication."
            )
            events.extend(
                self._create_linked_artifact_events(
                    incident_extra_data,
                    main_alert,
                )
            )

        return events

    def _create_incident_event(
        self,
        incident: IncidentInfo,
    ) -> SingleJson:
        incident_event: SingleJson = dict_to_flat(incident.to_json())
        incident_event = self._clean_flat_event(incident_event)
        incident_event[constants.EVENT_TYPE_KEY] = constants.EVENT_TYPE_INCIDENT

        return incident_event

    def _create_alert_events(
        self,
        incident_extra_data: IncidentExtraData,
        main_alert: Alert | None = None,
    ) -> list[SingleJson]:
        alert_events: list[SingleJson] = []
        alerts_to_process: list[Alert] = self._get_alerts_for_event_creation(
            incident_extra_data, main_alert
        )

        for alert in alerts_to_process:
            alert_events.append(self._build_alert_event(alert))

        return alert_events

    def _is_alert_below_severity_threshold(
        self,
        alert: Alert,
    ) -> bool:
        if not self.params.lowest_alert_severity_to_fetch:
            return False

        try:
            threshold_index: int = SEVERITY_RANK.get(
                self.params.lowest_alert_severity_to_fetch.lower(),
                invalid_sev_rank,
            )
            alert_severity_index: int = SEVERITY_RANK.get(
                alert.severity.lower(),
                invalid_sev_rank,
            )

            if invalid_sev_rank in (threshold_index, alert_severity_index):
                raise ValueError("Invalid severity value encountered.")

            if alert_severity_index < threshold_index:
                self.logger.info(
                    f"Alert {alert.alert_id} has severity '{alert.severity.lower()}', "
                    "which is below the threshold. Skipping event creation for this "
                    "alert."
                )
                return True

        except (ValueError, AttributeError):
            self.logger.info(
                f"Could not determine severity for alert {alert.alert_id} or "
                f"threshold. It will not be filtered by severity."
            )

        return False

    def _build_alert_event(self, alert: Alert) -> SingleJson:
        if alert.raw_data.get(constants.API_FW_MISC_KEY) is None:
            alert.raw_data[constants.API_FW_MISC_KEY] = ""

        alert_event: SingleJson = dict_to_flat(alert.to_json())
        alert_event = self._clean_flat_event(alert_event)
        alert_event[constants.EVENT_TYPE_KEY] = constants.EVENT_TYPE_ALERT

        return alert_event

    def _determine_severity_bypass_for_alert(
        self,
        incident: IncidentInfo,
        alert: Alert,
    ) -> bool:
        bypass_severity_filter: bool = self._should_bypass_alert_severity_filter(
            incident
        )

        if bypass_severity_filter:
            self.logger.info(
                f"Parent incident {incident.incident_id} meets the SmartScore "
                f"threshold. Alert {alert.alert_id} will be processed regardless of "
                "its severity."
            )
        return bypass_severity_filter

    def _create_all_artifact_events(
        self,
        incident_extra_data: IncidentExtraData,
    ) -> list[SingleJson]:
        artifact_events: list[SingleJson] = []
        reference_timestamp: int | None = self._get_reference_timestamp_for_artifacts(
            incident_extra_data
        )

        if constants.EVENT_TYPE_FILE not in self.params.artifacts_to_ignore:
            for artifact in incident_extra_data.file_artifacts:
                artifact_events.append(
                    self._build_artifact_event(
                        artifact, constants.EVENT_TYPE_FILE,
                        reference_timestamp,
                    )
                )

        if constants.EVENT_TYPE_NETWORK not in self.params.artifacts_to_ignore:
            for artifact in incident_extra_data.network_artifacts:
                artifact_events.append(
                    self._build_artifact_event(
                        artifact, constants.EVENT_TYPE_NETWORK,
                        reference_timestamp,
                    )
                )

        return artifact_events

    def _create_linked_artifact_events(
        self,
        incident_extra_data: IncidentExtraData,
        main_alert: Alert | None = None,
    ) -> list[SingleJson]:
        artifact_events: list[SingleJson] = []
        processed_file_hashes: set[str] = set()
        processed_network_ips: set[str] = set()

        alerts_to_scan: list[Alert] = (
            [main_alert] if main_alert else incident_extra_data.alerts
        )

        alert: Alert
        for alert in alerts_to_scan:
            if not alert:
                continue

            artifact_events.extend(
                self._collect_linked_file_artifact_events(
                    alert, incident_extra_data,
                    processed_file_hashes,
                )
            )
            artifact_events.extend(
                self._collect_linked_network_artifact_events(
                    alert,
                    incident_extra_data,
                    processed_network_ips,
                )
            )

        return artifact_events

    def _collect_linked_file_artifact_events(
        self,
        alert: Alert,
        incident_extra_data: IncidentExtraData,
        processed_hashes: set[str],
    ) -> list[SingleJson]:
        return self._collect_linked_artifact_events(
            alert=alert,
            incident_extra_data=incident_extra_data,
            processed_ids=processed_hashes,
            get_artifacts_func=self._get_alert_file_artifacts,
            artifact_id_key=constants.FILE_SHA256_KEY,
            event_type=constants.EVENT_TYPE_FILE,
        )

    def _collect_linked_network_artifact_events(
        self,
        alert: Alert,
        incident_extra_data: IncidentExtraData,
        processed_ips: set[str],
    ) -> list[SingleJson]:
        return self._collect_linked_artifact_events(
            alert=alert,
            incident_extra_data=incident_extra_data,
            processed_ids=processed_ips,
            get_artifacts_func=self._get_alert_network_artifacts,
            artifact_id_key=constants.NETWORK_REMOTE_IP_KEY,
            event_type=constants.EVENT_TYPE_NETWORK,
        )

    def _collect_linked_artifact_events(
        self,
        alert: Alert,
        incident_extra_data: IncidentExtraData,
        processed_ids: set[str],
        get_artifacts_func: Callable[
            [IncidentExtraData, Alert],
            list[FileArtifact | NetworkArtifact],
        ],
        artifact_id_key: str,
        event_type: str,
    ) -> list[SingleJson]:
        if event_type in self.params.artifacts_to_ignore:
            return []

        events: list[SingleJson] = []
        reference_timestamp: int | None = self._get_alert_reference_timestamp(alert)
        artifacts: list[FileArtifact | NetworkArtifact] = get_artifacts_func(
            incident_extra_data,
            alert,
        )

        for artifact in artifacts:
            artifact_id: str | None = artifact.raw_data.get(artifact_id_key)
            if artifact_id and artifact_id not in processed_ids:
                events.append(
                    self._build_artifact_event(
                        artifact, event_type,
                        reference_timestamp,
                    )
                )
                processed_ids.add(artifact_id)

        return events

    def _build_artifact_event(
        self,
        artifact: FileArtifact | NetworkArtifact,
        event_type: str,
        reference_timestamp: int | None,
    ) -> SingleJson:
        artifact_event: SingleJson = dict_to_flat(artifact.to_json())
        artifact_event = self._clean_flat_event(artifact_event)
        artifact_event[constants.EVENT_TYPE_KEY] = event_type
        if reference_timestamp:
            artifact_event[constants.API_EVENT_TIMESTAMP_KEY] = reference_timestamp

        return artifact_event

    def _get_alert_reference_timestamp(self, main_alert: Alert) -> int | None:
        return main_alert.raw_data.get(
            constants.API_EVENT_TIMESTAMP_KEY
        ) or main_alert.raw_data.get(constants.API_DETECTION_TIMESTAMP_KEY)

    def _get_alert_file_artifacts(
        self,
        incident_extra_data: IncidentExtraData,
        main_alert: Alert,
    ) -> list[FileArtifact]:
        return self._get_alert_artifacts(
            main_alert=main_alert,
            alert_key=constants.ACTION_FILE_SHA256_KEY,
            artifact_key=constants.FILE_SHA256_KEY,
            artifacts_list=incident_extra_data.file_artifacts,
        )

    def _get_alert_network_artifacts(
        self,
        incident_extra_data: IncidentExtraData,
        main_alert: Alert,
    ) -> list[NetworkArtifact]:
        return self._get_alert_artifacts(
            main_alert=main_alert,
            alert_key=constants.ACTION_REMOTE_IP_KEY,
            artifact_key=constants.NETWORK_REMOTE_IP_KEY,
            artifacts_list=incident_extra_data.network_artifacts,
        )

    def _get_alert_artifacts(
        self,
        main_alert: Alert,
        alert_key: str,
        artifact_key: str,
        artifacts_list: list[T_Artifact],
    ) -> list[T_Artifact]:
        key_value: str | None = main_alert.raw_data.get(alert_key)
        if not key_value:
            return []

        return [
            artifact
            for artifact in artifacts_list
            if artifact.raw_data.get(artifact_key) == key_value
        ]

    def _get_alerts_for_event_creation(
        self,
        incident_extra_data: IncidentExtraData,
        main_alert: Alert | None,
    ) -> list[Alert]:
        alerts_to_consider: list[Alert] = (
            [main_alert] if main_alert else incident_extra_data.alerts
        )

        incident: IncidentInfo = incident_extra_data.incident
        if self._should_bypass_alert_severity_filter(incident):
            self.logger.info(
                f"Incident {incident.incident_id} meets the SmartScore threshold. "
                f"All its alerts will be processed regardless of their severity."
            )
            return alerts_to_consider

        processable_alerts: list[Alert] = []
        for alert in alerts_to_consider:
            if not self._is_alert_below_severity_threshold(alert):
                processable_alerts.append(alert)

        return processable_alerts

    def _get_and_validate_incident_alerts(
        self,
        incident: IncidentInfo,
    ) -> IncidentExtraData | None:
        extra_data: IncidentExtraData = self.manager.get_extra_incident_data(
            incident.incident_id,
        )

        if self.params.lowest_alert_severity_to_fetch:
            processable_alerts: list[
                Alert
            ] = self._get_alerts_for_event_creation(extra_data, None)
            if not processable_alerts:
                self.logger.info(
                    f"Incident {incident.incident_id} meets incident-level filters, but"
                    " none of its alerts meet the 'Lowest Alert Severity To Fetch' "
                    "threshold. Skipping incident."
                )
                return None

        return extra_data

    def _clean_flat_event(
        self,
        event: SingleJson,
    ) -> SingleJson:
        return {
            key: (None if value == constants.NONE_AS_STRING else value)
            for key, value in event.items()
        }

    def _is_skipped_by_whitelist(
        self,
        value_to_check: str,
        is_in_list: bool,
    ) -> bool:
        if not is_in_list:
            self.logger.info(
                f"'{value_to_check}' is not present in the whitelist (allow list). "
                "Skipping."
            )
            return True

        return False

    def _is_skipped_by_blocklist(
        self,
        value_to_check: str,
        is_in_list: bool,
    ) -> bool:
        if is_in_list:
            self.logger.info(
                f"'{value_to_check}' is present in the blocklist (skip list). Skipping."
            )
            return True

        return False

    def _should_skip_by_dynamic_list(
        self,
        value_to_check: str,
    ) -> bool:
        if not self.siemplify.whitelist:
            return False

        lower_whitelist = {item.lower() for item in self.siemplify.whitelist}
        is_in_list = value_to_check.lower() in lower_whitelist

        is_blocklist_mode = (
            str(self.params.use_dynamic_list_as_a_blocklist).lower()
            == constants.TRUE_AS_STRING
        )

        if is_blocklist_mode:
            return self._is_skipped_by_blocklist(value_to_check, is_in_list)

        return self._is_skipped_by_whitelist(value_to_check, is_in_list)

    def _filter_alerts_by_dynamic_list(
        self,
        alerts: list[Alert],
    ) -> list[Alert]:
        filtered_alerts: list[Alert] = []
        for alert in alerts:
            source = alert.raw_data.get(constants.API_SOURCE_KEY, "")
            if not self._should_skip_by_dynamic_list(source):
                filtered_alerts.append(alert)

        return filtered_alerts

    def _get_reference_timestamp_for_artifacts(
        self,
        incident_extra_data: IncidentExtraData,
    ) -> int | None:
        if incident_extra_data.alerts:
            try:
                main_alert: Alert = max(
                    incident_extra_data.alerts,
                    key=lambda a: SEVERITY_RANK.get(
                        a.severity.lower(),
                        invalid_sev_rank,
                    ),
                )
                return main_alert.raw_data.get(
                    constants.API_EVENT_TIMESTAMP_KEY
                ) or main_alert.raw_data.get(constants.API_CREATION_TIME_KEY)
            except (ValueError, IndexError):
                self.logger.info(
                    "Could not determine a reference timestamp from alerts for incident"
                    f" {incident_extra_data.incident.incident_id}. Falling back to "
                    "incident creation time."
                )

        return incident_extra_data.incident.creation_time

    def _should_bypass_alert_severity_filter(
        self,
        incident: IncidentInfo,
    ) -> bool:
        """
        Checks if an incident's SmartScore meets the threshold to bypass alert
        severity filtering.

        Args:
            incident (IncidentInfo): The incident to evaluate.

        Returns:
            bool: True if the alert severity filter should be bypassed, False otherwise.
        """
        min_score: int | None = self.params.lowest_incident_smart_score_to_fetch
        return self.connector.incident_passes_score_filter(incident, min_score)


class XDRConnector(Connector):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connector_starting_time: int = unix_now()
        self.context.processed_cases: list[CaseInfo] = []
        self.context.failed_incident_ids: list[str] = []
        self.context.newly_processed_ids_for_context: list[str] = []
        self.case_processor: CaseProcessor | None = None

    def extract_params(self) -> None:
        """Extract and validate connector parameters."""
        super().extract_params()
        self.integration_params: IntegrationParameters = get_integration_parameters(
            self.siemplify,
        )

        self.params.include_historical_artifacts: bool = (
            str(self.params.include_historical_artifacts).lower()
            == constants.TRUE_AS_STRING
        )

        status_filter_str: str = self.params.status_filter or ""
        self.params.status_filter = string_to_multi_value(
            string_value=status_filter_str,
        )

        artifacts_to_ignore_str: str = self.params.artifacts_to_ignore or ""
        self.params.artifacts_to_ignore = string_to_multi_value(
            string_value=artifacts_to_ignore_str,
            only_unique=True,
        )

    def validate_params(self) -> None:
        """Validate the provided connector parameters."""
        validator = ParameterValidator(self.siemplify)

        self.params.max_days_backwards = validator.validate_positive(
            param_name="Max Days Backwards",
            value=self.params.max_days_backwards,
        )
        validator.validate_range(
            param_name="Alerts Count Limit",
            value=self.params.alerts_count_limit,
            min_limit=constants.MIN_ALERTS_LIMIT,
            max_limit=constants.MAX_RANGE_LIMIT,
        )
        if self.params.lowest_incident_smart_score_to_fetch:
            validator.validate_range(
                param_name="Lowest Incident SmartScore To Fetch",
                value=self.params.lowest_incident_smart_score_to_fetch,
                min_limit=constants.MIN_RANGE_LIMIT,
                max_limit=constants.MAX_RANGE_LIMIT,
            )

        for severity_param, name in [
            (
                self.params.lowest_incident_severity_to_fetch,
                constants.LOWEST_INCIDENT_SEVERITY_TO_FETCH_NAME,
            ),
            (
                self.params.lowest_alert_severity_to_fetch,
                constants.LOWEST_ALERT_SEVERITY_TO_FETCH_NAME,
            ),
        ]:
            if (
                severity_param
                and severity_param.lower() not in constants.SEVERITY_ORDER
            ):
                raise PaloAltoXdrValidationError(
                    f"Invalid value '{severity_param}' was provided for '{name}'. "
                    f"Possible values are: {', '.join(constants.SEVERITY_ORDER)}."
                )

    def init_managers(self) -> None:
        """Initialize the API manager and environment manager."""
        authenticator: AuthenticatedSession = AuthenticatedSession()
        session: requests.Session = authenticator.authenticate_session(
            self.integration_params
        )
        session.verify = self.integration_params.verify_ssl
        api_params: ApiParameters = ApiParameters(
            api_root=self.integration_params.api_root
        )
        self.manager: XDRManager = XDRManager(
            session=session, api_params=api_params, logger=self.logger
        )

        map_file: str = os.path.join(self.siemplify.run_folder, constants.MAP_FILE)
        self.environment_common = (
            GetEnvironmentCommonFactory.create_environment_manager(
                self.siemplify,
                self.params.environment_field_name,
                self.params.environment_regex_pattern,
                map_file,
            )
        )
        self.case_processor = CaseProcessor(self)

    def get_last_success_time(self) -> datetime.datetime:
        """
        Get the connector's last success time, ensuring it's within the
        allowed range.

        Returns:
            datetime.datetime
        """
        last_run_time: datetime.datetime = self.siemplify.fetch_timestamp(
            datetime_format=True
        )
        self.context.last_run_time = self._validate_timestamp(
            last_run_time, self.params.max_days_backwards
        )
        self.logger.info(f"Last run time is: {self.context.last_run_time}")

        return self.context.last_run_time

    def read_context_data(self) -> None:
        """
        Read the list of already processed IDs from the connector's context.

        Returns:
            None
        """
        connector_identifier: str = self.siemplify.context.connector_info.identifier
        raw_ids_data: str | None = self.siemplify.get_connector_context_property(
            connector_identifier,
            constants.EXISTING_IDS_KEY,
        )

        if not raw_ids_data:
            self.context.existing_ids = []
            self.logger.info(
                "No existing IDs found in context. Initializing an empty list."
            )
            return

        try:
            self.context.existing_ids = json.loads(raw_ids_data)
            self.logger.info(
                f"Successfully loaded {len(self.context.existing_ids)} "
                f"existing incident/alert IDs from context."
            )
        except (json.JSONDecodeError, TypeError):
            self.logger.error(
                "Failed to decode existing_ids from context. Starting with an empty "
                "list."
            )
            self.context.existing_ids = []

    def get_alerts(self) -> list[IncidentInfo]:
        """
        Fetch incidents from Cortex XDR and perform client-side filtering.

        Returns:
            list[IncidentInfo]: A list of filtered incident dictionaries to be
            processed.
        """
        self.logger.info("Fetching incidents...")

        incidents: list[IncidentInfo] = self._fetch_incidents_from_api()
        self.logger.info(f"Fetched {len(incidents)} raw incidents from the API.")
        self.context.fetched_incidents = incidents

        filtered_incidents: list[IncidentInfo] = self._filter_incidents(incidents)

        self.context.all_incidents = filtered_incidents
        self.logger.info(
            f"Processing {len(self.context.all_incidents)} incidents after all "
            "filters have been applied."
        )

        return self.context.all_incidents

    def process_alerts(
        self,
        alerts: list[IncidentInfo],
    ) -> tuple[list[CaseInfo], list[str]]:
        """
        Process fetched incidents into Siemplify cases.

        Args:
            alerts (list[IncidentInfo]): The list of incidents to process.

        Returns:
            tuple[list[CaseInfo], list[str]]: A tuple containing the list of
            created CaseInfo objects and a list of newly processed IDs.
        """
        incident: IncidentInfo
        for incident in alerts:
            if is_approaching_timeout(
                self.connector_starting_time,
                self.params.python_process_timeout,
            ):
                self.logger.info(
                    "Timeout is approaching. Stopping connector execution."
                )
                break

            self.logger.info(f"Processing incident {incident.incident_id}.")
            cases: list[CaseInfo]
            ids: list[str]
            cases, ids = self.case_processor.process_single_incident(incident)
            self.context.processed_cases.extend(cases)
            self.context.newly_processed_ids_for_context.extend(ids)

        self.logger.info(f"Created {len(self.context.processed_cases)} cases.")

        return (
            self.context.processed_cases,
            self.context.newly_processed_ids_for_context,
        )

    def create_alert_info(
        self,
        incident: IncidentInfo,
    ) -> CaseInfo:
        """
        Create a lightweight CaseInfo object from a raw incident dictionary.
        This method is required by the base Connector class for overflow checks.

        Args:
            incident (IncidentInfo): A raw incident dictionary from the API.

        Returns:
            CaseInfo: A CaseInfo object representing the alert.
        """
        case: CaseInfo = CaseInfo()
        case.name = incident.description or constants.DEFAULT_NAME
        case.ticket_id = incident.incident_id
        case.display_id = str(incident.incident_id)
        case.identifier = str(incident.incident_id)
        case.device_vendor = constants.VENDOR
        case.device_product = constants.PRODUCT
        case.priority = self.get_priority(incident.severity)
        case.start_time = incident.creation_time or 1
        case.end_time = incident.modification_time or 1
        case.rule_generator = case.name
        case.environment = (
            self.environment_common.get_environment(incident.to_json())
            or self.siemplify.context.connector_info.environment
        )
        return case

    def is_overflow_alert(
        self,
        alert_info: CaseInfo,
    ) -> bool:
        """
        Check if an alert is an overflow alert.

        Args:
            alert_info (CaseInfo): The alert info object to check.

        Returns:
            bool: True if the alert is an overflow, False otherwise.
        """
        return not self.params.disable_overflow and super().is_overflow_alert(
            alert_info
        )

    def set_last_success_time(
        self,
        _alerts: list[CaseInfo],
    ) -> None:
        """
        Set the last success time based on the modification time of the last
        fetched incident.

        Args:
            _alerts (list[CaseInfo]): Not used. Present for compatibility with
            the base class.

        Returns:
            None
        """
        if not self.context.fetched_incidents:
            self.logger.info("No new incidents found. Last run time remains unchanged.")
            return

        last_modification_time: int = max(
            incident.modification_time or 0
            for incident in self.context.fetched_incidents
        )
        new_timestamp: datetime.datetime = datetime.datetime.fromtimestamp(
            (last_modification_time + 1) / 1000
        )
        self.siemplify.save_timestamp(new_timestamp=new_timestamp)
        self.logger.info(f"New last run time has been set to: {new_timestamp}")

    def write_context_data(
        self,
        _all_alerts: list[CaseInfo],
    ) -> None:
        """
        Write the updated list of processed IDs to the context, managing its size.

        Args:
            _all_alerts (list): Not used. Present for compatibility with the
            base class.

        Returns:
            None
        """
        newly_processed_ids: list[str] = self.context.newly_processed_ids_for_context

        if not newly_processed_ids:
            self.logger.info("No new IDs to write to the context.")
            return

        updated_ids: list[str] = self._get_updated_processed_ids(
            self.context.existing_ids, newly_processed_ids
        )

        connector_identifier: str = self.siemplify.context.connector_info.identifier
        self.siemplify.set_connector_context_property(
            connector_identifier, constants.EXISTING_IDS_KEY, json.dumps(updated_ids)
        )
        self.logger.info(f"Saved {len(updated_ids)} IDs to context.")

    def _fetch_incidents_from_api(self) -> list[IncidentInfo]:
        search_time: int = convert_datetime_to_unix_time(self.context.last_run_time)
        api_statuses: list[str] | None = self._prepare_status_filter()

        limit: int = self.params.alerts_count_limit
        if self.is_test_run:
            self.logger.info(
                "This is a test run. The number of incidents to fetch is limited to 1."
            )
            limit = 1

        mod_filter = constants.CortexModificationFilterEnum.GTE_MODIFICATION_TIME

        return self.manager.get_incidents(
            modification_time=search_time,
            modification_filter_enum=mod_filter,
            search_from=0,
            search_to=limit,
            sort_order=constants.CortexSortOrderEnum.SORT_BY_ASC_ORDER,
            sort_type=constants.CortexSortTypesEnum.SORT_BY_MODIFICATION_TIME,
            statuses=api_statuses,
        )

    def _get_updated_processed_ids(
        self,
        existing_ids: list[str],
        new_ids: list[str],
    ) -> list[str]:
        updated_ids: list[str] = existing_ids + new_ids
        original_count: int = len(updated_ids)

        truncated_ids: list[str] = updated_ids[-constants.MAX_IDS_TO_STORE:]

        if len(truncated_ids) < original_count:
            self.logger.info(
                f"Truncated the list of processed IDs from {original_count} to "
                f"{len(truncated_ids)} to maintain performance."
            )

        return truncated_ids

    def _map_user_statuses_to_api_statuses(self) -> set[str]:
        api_statuses: set[str] = set()
        status: str
        for status in self.params.status_filter:
            mapped_statuses: list[str] | None = constants.STATUS_MAPPING.get(
                status.lower()
            )
            if mapped_statuses:
                api_statuses.update(mapped_statuses)
            else:
                self.logger.info(
                    f"'{status}' is not a valid status filter and will be ignored. "
                    "Possible values are: "
                    f"{', '.join(constants.STATUS_MAPPING.keys())}."
                )

        return api_statuses

    def _prepare_status_filter(self) -> list[str] | None:
        if not self.params.status_filter:
            self.logger.info(
                "Status Filter is empty. Fetching incidents of all statuses."
            )
            return None

        api_statuses: set[str] = self._map_user_statuses_to_api_statuses()

        if not api_statuses:
            self.logger.info(
                "No valid statuses were found in the 'Status Filter' parameter. "
                "Fetching incidents of all statuses as a fallback."
            )
            return None

        self.logger.info(
            f"Filtering incidents with the following statuses: {list(api_statuses)}"
        )

        return list(api_statuses)

    def _get_min_severity_index(self) -> int:
        min_severity: str | None = self.params.lowest_incident_severity_to_fetch
        if not min_severity:
            return invalid_sev_rank

        min_severity_index: int = SEVERITY_RANK.get(
            min_severity.lower(),
            invalid_sev_rank,
        )
        if min_severity_index == invalid_sev_rank:
            self.logger.info(
                f"Invalid severity '{min_severity}' provided. Ignoring severity filter."
            )

        return min_severity_index

    def _incident_passes_severity_filter(
        self,
        incident: IncidentInfo,
        min_severity_index: int,
    ) -> bool:
        if min_severity_index == invalid_sev_rank:
            return False

        try:
            incident_severity_index: int = SEVERITY_RANK.get(
                incident.severity.lower(),
                invalid_sev_rank,
            )
            return (
                incident_severity_index != invalid_sev_rank
                and incident_severity_index >= min_severity_index
            )
        except AttributeError:
            return False

    def incident_passes_score_filter(
        self,
        incident: IncidentInfo,
        min_score: int | None,
    ) -> bool:
        """
        Check if an incident's aggregated score meets the minimum threshold.

        Args:
            incident (IncidentInfo): The incident to evaluate.
            min_score (int | None): The minimum score required to pass the filter.

        Returns:
            bool: True if the incident's score is at or above the minimum,
            False otherwise.
        """
        if min_score is None:
            return False

        return (incident.aggregated_score or 0) >= min_score

    def _should_keep_incident(
        self,
        incident: IncidentInfo,
        min_severity_index: int,
        min_score: int | None,
    ) -> bool:
        min_severity_param: str | None = self.params.lowest_incident_severity_to_fetch

        severity_passes: bool = self._incident_passes_severity_filter(
            incident,
            min_severity_index,
        )
        score_passes: bool = self.incident_passes_score_filter(incident, min_score)

        if min_severity_param and min_score is not None:
            return severity_passes or score_passes

        if min_severity_param:
            return severity_passes

        if min_score is not None:
            return score_passes

        return False

    def _filter_incidents(
        self,
        incidents: list[IncidentInfo],
    ) -> list[IncidentInfo]:
        min_severity_param: str | None = self.params.lowest_incident_severity_to_fetch
        min_score: int | None = self.params.lowest_incident_smart_score_to_fetch

        if not min_severity_param and min_score is None:
            return incidents

        self.logger.info(
            f"Applying filters. Min Severity: '{min_severity_param}', "
            f"Min Score: '{min_score}'."
        )

        min_severity_index: int = self._get_min_severity_index()

        filtered_incidents: list[IncidentInfo] = [
            incident
            for incident in incidents
            if self._should_keep_incident(incident, min_severity_index, min_score)
        ]

        self.logger.info(
            f"Found {len(filtered_incidents)} incidents after applying filters "
            f"(out of {len(incidents)})."
        )

        return filtered_incidents

    def get_priority(self, severity: str | None) -> int:
        """
        Map a Cortex XDR severity string to a Siemplify priority integer.

        Args:
            severity (str | None): The severity string from the incident or alert
            (e.g., "high", "medium").

        Returns:
            int: The corresponding Siemplify priority value (e.g., 100, 80, 60).
            Defaults to 40 if severity is not found.
        """
        return constants.PRIORITIES_MAP.get(
            severity.lower() if severity else "low", 40
        )

    def _validate_timestamp(
        self,
        last_run_timestamp: datetime.datetime,
        offset_days: int,
    ) -> datetime.datetime:
        max_timedelta: datetime.timedelta = datetime.timedelta(days=offset_days)
        if utc_now() - last_run_timestamp > max_timedelta:
            return utc_now() - max_timedelta

        return last_run_timestamp


def main() -> None:
    connector: XDRConnector = XDRConnector(
        constants.XDR_CONNECTOR_SCRIPT_NAME, is_test_run(sys.argv)
    )
    connector.start()


if __name__ == "__main__":
    main()

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
import abc

import dataclasses
from collections.abc import Iterable, MutableMapping
from typing import Any

from crowd_strike_falcon.core.CrowdStrikeParser import CrowdStrikeParser
from crowd_strike_falcon.core.datamodels import (
    AlertDetails,
    CustomIndicator,
    Detection,
    DetectionDetail,
    Device,
    File,
    HostGroup,
    IncidentDetails,
    LoginHistory,
    OnDemandScanData,
    OnlineState,
    Process,
    SearchEventsData,
    SubmissionReport,
    VulnerabilityDetail,
)
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import (
    AlreadyExistsError,
    IdNotFoundError,
)


@dataclasses.dataclass
class CrowdStrikeFalcon(abc.ABC):
    def __init__(self) -> None:
        self._alerts: MutableMapping[str, AlertDetails] = {}
        self._detections: MutableMapping[str, DetectionDetail] = {}
        self._incidents: MutableMapping[str, IncidentDetails] = {}
        self._host_groups: MutableMapping[str, HostGroup] = {}
        self._vulnerabilities: MutableMapping[str, VulnerabilityDetail] = {}
        self._processes: MutableMapping[str, Process] = {}
        self._devices: MutableMapping[str, Device] = {}
        self._custom_indicators: MutableMapping[str, CustomIndicator] = {}
        self._submission_reports: MutableMapping[str, SubmissionReport] = {}
        self._files: MutableMapping[str, File] = {}
        self._on_demand_scans: MutableMapping[str, OnDemandScanData] = {}
        self._login_histories: MutableMapping[str, LoginHistory] = {}
        self._online_states: MutableMapping[str, OnlineState] = {}
        self._stream_detections: MutableMapping[str, Detection] = {}
        self._search_events: dict[str, SearchEventsData] = {}

    def list_items(self, item_type: str) -> MutableMapping:
        """Lists the requested items based on the item type.

        Args:
            item_type (str): The type of items to list.
                             Options: 'alerts', 'detections', 'incidents',
                                      'host_groups', 'vulnerabilities', 'processes',
                                      'devices', 'custom_indicators',
                                      'suforbmission_reports', 'files',
                                      'on_demand_scans', 'login_histories',
                                      'online_states', 'stream_detections'.

        Returns:
            MutableMapping: The requested mapping.

        Raises:
            ValueError: If the item_type is invalid.

        """
        item_mapping = {
            "alerts": self._alerts,
            "detections": self._detections,
            "incidents": self._incidents,
            "host_groups": self._host_groups,
            "vulnerabilities": self._vulnerabilities,
            "processes": self._processes,
            "devices": self._devices,
            "custom_indicators": self._custom_indicators,
            "submission_reports": self._submission_reports,
            "files": self._files,
            "on_demand_scans": self._on_demand_scans,
            "login_histories": self._login_histories,
            "online_states": self._online_states,
            "stream_detections": self._stream_detections,
        }

        if item_type not in item_mapping:
            raise ValueError(
                f"Invalid item_type: {item_type}. Must be one of "
                f"{list(item_mapping.keys())}.",
            )

        return item_mapping[item_type]

    def add_entries(self, data_type: str, entries: Iterable[dict[str, Any]]) -> None:
        """Adds multiple entries on the specified data type.

        Args:
            data_type (str): The type of entries to add. Must be one of the following:
                - "alerts": Adds alerts to the system.
                - "detections": Adds detections to the system.
                - "incidents": Adds incidents to the system.
                - "host_groups": Adds host groups to the system.
                - "vulnerabilities": Adds vulnerabilities to the system.
                - "processes": Adds processes to the system.
                - "devices": Adds devices to the internal device registry.
                - "custom_indicators": Adds custom indicators to the system.
                - "submission_reports": Adds submission reports to the system.
                - "files": Adds files to the system.
                - "on_demand_scans": Adds on-demand scans to the system.
                - "login_histories": Adds login histories to the system.
                - "online_states": Adds online states to the system.
                - "stream_detections": Adds stream detections to the system.

            entries (Iterable[dict[str, Any]]): An iterable of dictionaries containing
                raw data for building the respective objects. Each dictionary must
                adhere to the expected format for the specified `data_type`.

        Raises:
            ValueError: If an unsupported `data_type` is provided.

        Returns:
            None

        """
        add_methods = {
            "alerts": self.add_alert,
            "detections": self.add_detection,
            "incidents": self.add_incident,
            "host_groups": self.add_host_group,
            "vulnerabilities": self.add_vulnerability,
            "processes": self.add_process,
            "devices": self.add_device,
            "custom_indicators": self.add_custom_indicator,
            "submission_reports": self.add_submission_report,
            "files": self.add_file,
            "on_demand_scans": self.add_on_demand_scan,
            "login_histories": self.add_login_history,
            "online_states": self.add_online_state,
            "stream_detections": self.add_stream_detection,
        }

        if data_type not in add_methods:
            raise ValueError(f"Unsupported data type: {data_type}")

        add_method = add_methods[data_type]
        for raw_data in entries:
            add_method(raw_data=raw_data)

    def get_custom_indicators(self, custom_indicator_id: str) -> CustomIndicator:
        """Retrieves the details of a custom indicator by its unique identifier.
        """
        if custom_indicator_id not in self._custom_indicators:
            raise IdNotFoundError(
                f"Invalid Custom Indicator ID {custom_indicator_id}",
            )
        return self._custom_indicators[custom_indicator_id]

    def add_custom_indicator(self, raw_data: dict[str, Any]) -> None:
        """Adds a custom indicator to the internal custom indicator registry.
        """
        parser = CrowdStrikeParser()
        custom_indicator: CustomIndicator = parser.build_siemplify_indicator_obj(
            raw_data,
        )

        if custom_indicator.value in self._custom_indicators:
            raise AlreadyExistsError("Custom Indicator already exists")

        self._custom_indicators[custom_indicator.value] = custom_indicator

    def get_alert(self, alert_id: str) -> AlertDetails:
        if alert_id not in self._alerts:
            raise IdNotFoundError(f"Invalid Alert ID {alert_id}")
        return self._alerts[alert_id]

    def add_alert(self, raw_data: dict[str, Any]) -> None:
        """Adds an alert to the internal alert registry.

        Args:
            raw_data (dict[str, Any]): A dictionary containing raw data for
            building the `AlertDetails` object. The data must include a valid
            alert ID.

        Raises:
            AlreadyExistsError: If an alert with the given ID
            already exists in the registry.

        Returns:
            None

        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        alert: AlertDetails = parser.build_siemplify_alert_details(raw_data)

        if alert.alert_id in self._alerts:
            raise AlreadyExistsError(f"Alert ID {alert.alert_id} already exists")

        self._alerts[alert.alert_id] = alert

    def update_alert(
            self,
            alert_id: str,
            status: str | None = None,
            comments: str | Iterable[str] | None = None,
    ) -> None:
        """Updates the status and/or comments of an alert.

        Args:
            alert_id (str): The unique identifier of the alert to update.
            status (str, optional): The new status to assign to the alert.
                If not provided, the status remains unchanged.
            comments (str or Iterable[str], optional): Comments to add to the alert.
                Can be a single comment (string)
                or multiple comments (iterable of strings).
                If not provided, no comments are added.

        Returns:
            None: This method does not return a value but updates
            the alert's data in place.

        """
        alert: AlertDetails = self.get_alert(alert_id)
        if status is not None:
            alert.raw_data["status"] = status
        if comments:
            alert.raw_data.setdefault(
                "comments", [],
            ).extend(comments if isinstance(comments, list) else [comments])

    def get_detection(self, detection_id: str) -> DetectionDetail:
        if detection_id not in self._detections:
            raise IdNotFoundError(f"Invalid Detection ID {detection_id}")
        return self._detections[detection_id]

    def add_detection(self, raw_data: dict[str, Any]) -> None:
        """Adds a detection to the internal detection registry.

        Args:
            raw_data (dict[str, Any]): A dictionary containing raw data for
            building the `DetectionDetail` object. The data must include a valid
            detection ID.

        Raises:
            AlreadyExistsError: If a detection with the given ID
            already exists in the registry.

        Returns:
            None

        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        detection: DetectionDetail = parser.build_siemplify_detection_detail(raw_data)

        if detection.detection_id in self._detections:
            raise AlreadyExistsError(
                f"Detection ID {detection.detection_id} already exists",
            )

        self._detections[detection.detection_id] = detection

    def get_incident(self, incident_id: str) -> IncidentDetails:
        if incident_id not in self._incidents:
            raise IdNotFoundError(f"Invalid Incident ID {incident_id}")
        return self._incidents[incident_id]

    def add_incident(self, raw_data: dict[str, Any]) -> None:
        """Adds an incident to the internal incident registry.

        Args:
            raw_data (dict[str, Any]): A dictionary containing raw data for
            building the `IncidentDetails` object. The data must include a valid
            incident ID.

        Raises:
            AlreadyExistsError: If an incident with the given ID
            already exists in the registry.

        Returns:
            None

        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        incident: IncidentDetails = parser.build_siemplify_incident_details(raw_data)

        if incident.incident_id in self._incidents:
            raise AlreadyExistsError(
                f"Incident ID {incident.incident_id} already exists",
            )

        self._incidents[incident.incident_id] = incident

    def update_detection(
            self,
            detection_id: str,
            status: str | None = None,
            comments: str | Iterable[str] | None = None,
    ) -> None:
        """Updates the status and/or comments of a detection.

        Args:
            detection_id (str): The unique identifier of the detection to update.
            status (str, optional): The new status to assign to the detection.
            If not provided, the status remains unchanged.
            comments (str or Iterable[str], optional): Comments to add to the detection.
                Can be a single comment (string)
                or multiple comments (iterable of strings).
                If not provided, no comments are added.

        Returns:
            None: This method does not return a value but updates
            the detection's data in place.

        """
        detection: DetectionDetail = self.get_detection(detection_id)
        if status is not None:
            detection.raw_data["status"] = status
        if comments:
            detection.raw_data.setdefault(
                "comments", [],
            ).extend(comments if isinstance(comments, list) else [comments])

    def update_incident(self,
            incident_id: str,
            status: str | None = None,
            comments: str | Iterable[str] | None = None,
    ) -> None:
        """Updates the details of an existing incident.

        Args:
            incident_id (str): The unique identifier of the incident to be updated.
            status (str | None): The new status to set for the incident. If `None`,
            the status is not updated.
            comments (str | Iterable[str] | None): Comments to add to the incident.
            This can be a single comment as a string or an iterable of strings.
            If `None`, no comments are added.

        Raises:
            KeyError: If the incident with the given ID does not exist.

        Returns:
            None

        """
        incident: IncidentDetails = self.get_incident(incident_id)
        if status is not None:
            incident.raw_data["status"] = status
        if comments:
            incident.raw_data.setdefault(
                "comments", [],
            ).extend(comments if isinstance(comments, list) else [comments])

    def get_device(self, device_id: str) -> Device:
        if device_id not in self._devices:
            raise IdNotFoundError(f"Invalid Device ID {device_id}")
        return self._devices[device_id]

    def add_device(self, raw_data: dict[str, Any]) -> None:
        """Adds a device to the internal device registry.

        Args:
            raw_data (dict[str, Any]): A dictionary containing raw data for
            building the `Device` object. Must include either an "id" field
            in the nested `raw_data` of the `Device` or a "device_id" key
            in the input `raw_data`.

        Raises:
            AlreadyExistsError: If a device with the given ID
            already exists in the registry.

        Returns:
            None

        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        device: Device = parser.build_siemplify_device_obj(raw_data)

        device_id = device.raw_data.get("id") or raw_data.get("device_id")
        if device_id in self._devices:
            raise AlreadyExistsError(f"Device ID {device_id} already exists")

        self._devices[device_id] = device

    def update_device(self, device_id: str, updates: dict[str, Any]) -> None:
        device: Device = self.get_device(device_id)
        for key, value in updates.items():
            setattr(device, key, value)

    def get_host_group(self, group_id: str) -> HostGroup:
        if group_id not in self._host_groups:
            raise IdNotFoundError(f"Invalid Host Group ID {group_id}")
        return self._host_groups[group_id]

    def add_host_group(self, raw_data: dict[str, Any]) -> None:
        """Adds a host group to the internal host group registry.

        Args:
            raw_data (dict[str, Any]): A dictionary containing raw data for
            building the `HostGroup` object. The data must include a valid
            host group ID.

        Raises:
            AlreadyExistsError: If a host group with the given
            ID already exists in the registry.

        Returns:
            None

        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        host_group: HostGroup = parser.build_host_group_object(raw_data)

        if host_group.id in self._host_groups:
            raise AlreadyExistsError(
                f"Host Group ID {host_group.id} already exists",
            )

        self._host_groups[host_group.id] = host_group

    def update_host_group(self, group_id: str, updates: dict[str, Any]) -> None:
        host_group: HostGroup = self.get_host_group(group_id)
        for key, value in updates.items():
            setattr(host_group, key, value)

    def get_vulnerability(self, vulnerability_id: str) -> VulnerabilityDetail:
        """Retrieves the details of a vulnerability by its unique identifier.

        Args:
            vulnerability_id (str): The unique identifier of the
                                    vulnerability to retrieve.

        Returns:
            VulnerabilityDetail: An object containing the details of
                                the requested vulnerability.

        """
        if vulnerability_id not in self._vulnerabilities:
            raise IdNotFoundError(
                f"Invalid Vulnerability ID {vulnerability_id}",
            )
        return self._vulnerabilities[vulnerability_id]

    def add_vulnerability(self, raw_data: dict[str, Any]) -> None:
        """Adds a vulnerability to the internal vulnerability registry.

        Args:
            raw_data (dict[str, Any]): A dictionary containing raw data for
            building the `VulnerabilityDetail` object. The data must include a
            valid CVE ID.

        Raises:
            AlreadyExistsError: If a vulnerability with the given
            CVE ID already exists in the registry.

        Returns:
            None

        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        vulnerability: VulnerabilityDetail = parser.build_vulnerability_detail_obj(
            raw_data,
        )

        if vulnerability.cve_id in self._vulnerabilities:
            raise AlreadyExistsError(
                f"Vulnerability ID {vulnerability.cve_id} already exists",
            )

        self._vulnerabilities[vulnerability.cve_id] = vulnerability

    def update_vulnerability(
            self,
            vulnerability_id: str,
            updates: dict[str, Any],
    ) -> None:
        """Updates a vulnerability's details based on the provided updates.

        Args:
            vulnerability_id (str): The unique identifier of the vulnerability to
                update.
            updates (dict[str, Any]): A dictionary of updates, where keys are attribute
                names and values are the new values for those attributes.

        Returns:
            None: This method does not return a value but updates
                the vulnerability in place.

        Raises:
            IdNotFoundError: If the provided `vulnerability_id`
                does not exist.

        """
        vulnerability: VulnerabilityDetail = self.get_vulnerability(vulnerability_id)
        for key, value in updates.items():
            setattr(vulnerability, key, value)

    def get_process(self, process_id: str) -> Process:
        if process_id not in self._processes:
            raise IdNotFoundError(f"Invalid Process ID {process_id}")
        return self._processes[process_id]

    def add_process(self, raw_data: dict[str, Any]) -> None:
        """Adds a process to the internal process registry.

        Args:
            raw_data (dict[str, Any]): A dictionary containing raw data for
            building the process object. Must include either an "id" field
            in the nested `raw_data` of the `Process` or a "process_id" key
            in the input `raw_data`.

        Raises:
            AlreadyExistsError: If a process with the given ID
            already exists in the registry.

        Returns:
            None

        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        process: Process = parser.build_siemplify_process(raw_data)

        process_id: str = (
            process.raw_data.get("id") or raw_data.get("process_id")
        )
        if process_id in self._processes:
            raise AlreadyExistsError(f"Process ID {process_id} already exists")

        self._processes[process_id] = process

    def update_process(self, process_id: str, updates: dict[str, Any]) -> None:
        process: Process = self.get_process(process_id)
        for key, value in updates.items():
            setattr(process, key, value)

    def get_submission_report(self, submission_report_id: str) -> SubmissionReport:
        """Retrieves the details of a submission report by its unique identifier.
        """
        if submission_report_id not in self._submission_reports:
            raise IdNotFoundError(
                f"Invalid Submission Report ID {submission_report_id}",
            )
        return self._submission_reports[submission_report_id]

    def add_submission_report(self, raw_data: dict[str, Any]) -> None:
        """Adds a submission report to the internal submission report registry.
        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        submission_report: SubmissionReport = parser.build_submission_reports(raw_data)

        submission_report_id: str = submission_report[0].raw_data.get("id")
        if submission_report_id in self._submission_reports:
            raise AlreadyExistsError(
                f"Submission Report ID {submission_report_id} already exists",
            )

        self._submission_reports[submission_report_id] = submission_report

    def get_file(self, file_id: str) -> File:
        if file_id not in self._files:
            raise IdNotFoundError(f"Invalid File ID {file_id}")
        return self._files[file_id]

    def add_file(self, raw_data: dict[str, Any]) -> None:
        """Adds a file to the internal file registry.
        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        file: File = parser.build_file_objects(raw_data)

        file_id: str = file[0].raw_data.get("sha256")
        if file_id in self._files:
            raise AlreadyExistsError(f"File ID {file_id} already exists")

        self._files[file_id] = file

    def get_on_demand_scans(self, on_demand_scan_id: str) -> OnDemandScanData:
        if on_demand_scan_id not in self._on_demand_scans:
            raise IdNotFoundError(f"Invalid File ID {on_demand_scan_id}")
        return self._on_demand_scans[on_demand_scan_id]

    def add_on_demand_scan(self, raw_data: dict[str, Any]) -> None:
        """Adds a on demand scan to the internal on demand scan registry.
        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        on_demand_scan: OnDemandScanData = parser.build_on_demand_scan_data(raw_data)

        on_demand_scan_id: str = on_demand_scan.scan_id
        if on_demand_scan_id in self._on_demand_scans:
            raise AlreadyExistsError(f"File ID {on_demand_scan_id} already exists")

        self._on_demand_scans[on_demand_scan_id] = on_demand_scan

    def get_login_history(self, login_history_id: str) -> LoginHistory:
        if login_history_id not in self._login_histories:
            raise IdNotFoundError("Invalid Login History ID")
        return self._login_histories[login_history_id]

    def add_login_history(self, raw_data: dict[str, Any]) -> None:
        """Adds a login history to the internal login history registry.
        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        login_history: LoginHistory = parser.build_login_history_object(raw_data)
        login_history_id: str = login_history.device_id
        if login_history_id in self._login_histories:
            raise AlreadyExistsError(
                f"File ID {login_history_id} already exists",
            )

        self._login_histories[login_history.device_id] = login_history

    def get_online_state(self, online_state_id: str) -> OnlineState:
        if online_state_id not in self._online_states:
            raise IdNotFoundError("Invalid Online State ID")
        return self._online_states[online_state_id]

    def add_online_state(self, raw_data: dict[str, Any]) -> None:
        """Adds an online state to the internal online state registry.
        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        online_state: OnlineState = parser.build_online_state_object(raw_data)
        online_state_id: str = online_state.device_id
        if online_state_id in self._online_states:
            raise AlreadyExistsError(
                f"File ID {online_state_id} already exists",
            )
        self._online_states[online_state.device_id] = online_state

    def get_stream_detection(self, stream_detection_id: str) -> Detection:
        """Retrieves the details of a stream detection by its unique identifier.
        """
        if stream_detection_id not in self._stream_detections:
            raise IdNotFoundError(
                f"Invalid Stream Detection ID {stream_detection_id}",
            )
        return self._stream_detections[stream_detection_id]

    def add_stream_detection(self, raw_data: dict[str, Any]) -> None:
        """Adds a stream detection to the internal stream detection registry.
        """
        parser: CrowdStrikeParser = CrowdStrikeParser()
        stream_detection: Detection = parser.build_siemplify_detection_obj(raw_data)
        stream_detection_id: str = stream_detection.detect_id

        if stream_detection_id in self._stream_detections:
            raise AlreadyExistsError(
                f"Stream Detection ID {stream_detection_id} already exists",
            )
        self._stream_detections[stream_detection_id] = stream_detection

    def get_events(self, job_id: str) -> SearchEventsData:
        """Retrieves the details of a search event by its unique identifier."""
        return self._search_events[job_id]

    def add_events(self, raw_data: SingleJson, job_id: str) -> None:
        """Adds a search event to the internal search event registry."""
        job: SearchEventsData = SearchEventsData.from_json(raw_data, job_id)
        self._search_events[job_id] = job

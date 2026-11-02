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
from TIPCommon.types import SingleJson

from crowd_strike_falcon.core.datamodels import (
    IncidentData,
    AlertDetails,
    BatchCommand,
    BatchSession,
    Behaviors,
    Command,
    CustomIndicator,
    Device,
    Detection,
    DetectionDetail,
    File,
    HostGroup,
    LoginHistory,
    VulnerabilityDetail,
    OnlineState,
    Process,
    RemediationDetail,
    Stream,
    SubmissionData,
    SubmissionReport,
    ThreatGraphDevice,
    VertexDetails,
    IncidentDetails,
    BehaviorDetails,
    OnDemandScanData,
    SearchEventsData,
)

class CrowdStrikeParser:
    def build_results(
        self,
        raw_json,
        method,
        data_key="resources",
        pure_data=False,
        limit=None,
        **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    def get_next_page_cursor(self, raw_json):
        return self.get_pagination(raw_json).get("next_page")

    def get_page_total(self, raw_json):
        return self.get_pagination(raw_json).get("total", 0)

    def get_page_offset(self, raw_json):
        return self.get_pagination(raw_json).get("offset")

    def get_page_after_token(self, raw_json: SingleJson) -> str | None:
        """Extracts the 'after' token for pagination from the raw JSON response.

        Args:
            raw_json: The raw JSON response from the API.

        Returns:
            The 'after' token if present, otherwise None.
        """
        return self.get_pagination(raw_json).get("after")

    @staticmethod
    def get_pagination(raw_json):
        return raw_json.get("meta", {}).get("pagination", {})

    def build_batch_session_object(self, raw_json, device_id):
        return BatchSession(
            raw_data=self.get_resources(raw_json),
            batch_id=raw_json.get("batch_id"),
            device_id=device_id,
        )

    def build_batch_get_obj(self, raw_json):
        return raw_json.get("batch_get_cmd_req_id")

    def build_batch_command_obj(self, raw_json):
        return BatchCommand(raw_json, **raw_json)

    def get_session_id(self, raw_json):
        return raw_json.get("session_id")

    def get_cloud_request_id(self, raw_json):
        return raw_json.get("cloud_request_id")

    def build_command_object(self, raw_data):
        return Command(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_siemplify_indicator_obj(indicator_data):
        return CustomIndicator(indicator_data, **indicator_data)

    def get_resources_dict(self, raw_json, builder_method=None):
        resources = raw_json.get("resources", {})
        return (
            [
                getattr(self, builder_method)(resource_json)
                for resource_json in resources.values()
            ]
            if builder_method
            else resources
        )

    def get_resources(self, raw_json, builder_method=None):
        resources = raw_json.get("resources", [])
        return (
            [
                getattr(self, builder_method)(resource_json)
                for resource_json in resources
            ]
            if builder_method
            else resources
        )

    def build_siemplify_detection_detail(self, detection_details_json):
        return DetectionDetail(
            raw_data=detection_details_json,
            first_behavior=detection_details_json.get("first_behavior"),
            last_behavior=detection_details_json.get("last_behavior"),
            detection_id=(
                detection_details_json.get("composite_id")
                or detection_details_json.get("detection_id")
            ),
            max_severity=detection_details_json.get("max_severity"),
            behaviors=[
                self.build_siemplify_detection_behavior(behavior_json)
                for behavior_json in detection_details_json.get("behaviors", [])
            ],
            max_severity_name=detection_details_json.get("max_severity_displayname"),
        )

    @staticmethod
    def build_siemplify_alert_details(raw_data):
        return AlertDetails(
            raw_data=raw_data,
            alert_id=raw_data.get("id"),
            composite_id=(
                raw_data.get("composite_id")
                or raw_data.get("detection_id")
            ),
            display_name=raw_data.get("display_name"),
            description=raw_data.get("description"),
            product=raw_data.get("product"),
            severity=raw_data.get("severity"),
            type_=raw_data.get("type"),
            start_time=raw_data.get("start_time"),
            end_time=raw_data.get("end_time"),
            created_timestamp=raw_data.get("created_timestamp"),
            updated_timestamp=raw_data.get("updated_timestamp"),
        )

    def build_siemplify_detection_behavior(self, behavior_json):
        return Behaviors(
            raw_data=behavior_json,
            scenario=behavior_json.get("scenario"),
            severity=behavior_json.get("severity"),
        )

    @staticmethod
    def build_siemplify_incident_details(raw_data):
        raw_data["data_type"] = "Incident Data"
        return IncidentDetails(
            raw_data=raw_data,
            incident_type=raw_data.get("incident_type"),
            incident_id=raw_data.get("incident_id"),
            first_hostname=(raw_data.get("hosts") or [{}])[0].get("hostname"),
            severity=raw_data.get("fine_score"),
            first_tactics=(raw_data.get("tactics") or [{}])[0],
            start_time=raw_data.get("start"),
            end_time=raw_data.get("end"),
        )

    @staticmethod
    def build_siemplify_incident_behaviors_details(raw_data):
        raw_data["data_type"] = "Behavior"
        return BehaviorDetails(raw_data=raw_data)

    @staticmethod
    def build_siemplify_device_obj(device_data):
        return Device(raw_data=device_data, **device_data)

    @staticmethod
    def get_event_data(detection_data):
        return detection_data.get("event", {})

    @staticmethod
    def get_offset(detection_data):
        return detection_data.get("metadata", {}).get("offset")

    @staticmethod
    def build_siemplify_detection_obj(detection_data):
        return Detection(
            raw_data=detection_data,
            event_type=detection_data.get("metadata", {}).get("eventType"),
            offset=detection_data.get("metadata", {}).get("offset"),
            event_creation_time=detection_data.get("metadata", {}).get(
                "eventCreationTime"
            ),
            severity=detection_data.get("event", {}).get("Severity"),
            detect_id=(
                detection_data.get("event", {}).get("CompositeId")
                or detection_data.get("event", {}).get("DetectId")
            ),
            detect_name=(
                detection_data.get("event", {}).get("Name")
                or detection_data.get("event", {}).get("DetectName")
            ),
            detect_description=(
                detection_data.get("event", {}).get("Description")
                or detection_data.get("event", {}).get("DetectDescription")
            ),
            operation_name=detection_data.get("event", {}).get("OperationName"),
            service_name=detection_data.get("event", {}).get("ServiceName"),
            session_id=detection_data.get("event", {}).get("SessionId"),
            audit_information={
                audit_info["Key"]: audit_info["ValueString"]
                for audit_info in detection_data.get("event", {}).get(
                    "AuditKeyValues", []
                )
            },
        )

    @staticmethod
    def build_siemplify_vertex_details_obj(vertex_data):
        return VertexDetails(vertex_data)

    @staticmethod
    def build_siemplify_threatgraph_device(device_data):
        return ThreatGraphDevice(
            raw_data=device_data,
            device_id=device_data.get("device_id"),
            path=device_data.get("path"),
        )

    @staticmethod
    def build_siemplify_process(process_data, hostname=None, indicator_value=None):
        return Process(
            raw_data=process_data,
            indicator_value=indicator_value,
            hostname=hostname,
            process_name=process_data.get("file_name"),
            **process_data
        )

    def build_siemplify_stream(self, stream_data):
        resource = (self.get_resources(stream_data) or [{}])[0]
        return Stream(
            raw_data=stream_data,
            url=resource.get("dataFeedURL"),
            token=resource.get("sessionToken", {}).get("token"),
        )

    @staticmethod
    def get_detection_status(detection):
        return detection.get("status")

    @staticmethod
    def build_vulnerability_detail_obj(resources):
        return VulnerabilityDetail(
            raw_data=resources,
            ids=resources.get("remediation", {}).get("ids", []),
            severity=resources.get("cve", {}).get("severity"),
            cve_id=resources.get("cve", {}).get("id"),
            score=resources.get("cve", {}).get("base_score"),
            product_name_version=resources.get("app", {}).get("product_name_version"),
            **resources
        )

    @staticmethod
    def build_remediation_detail_obj(resources):
        return RemediationDetail(raw_data=resources, **resources)

    def get_after_page(self, raw_json):
        return self.get_pagination(raw_json).get("after")

    @staticmethod
    def build_host_group_object(raw_data):
        return HostGroup(
            raw_data=raw_data, id=raw_data.get("id"), name=raw_data.get("name")
        )

    @staticmethod
    def build_login_history_object(raw_data):
        return LoginHistory(
            raw_data=raw_data,
            device_id=raw_data.get("device_id"),
            recent_logins=raw_data.get("recent_logins"),
        )

    @staticmethod
    def build_online_state_object(raw_data):
        return OnlineState(
            raw_data=raw_data, device_id=raw_data.get("id"), state=raw_data.get("state")
        )

    @staticmethod
    def build_submissions_data(submissions_data):
        if submissions_data is not None:
            return [
                SubmissionData(
                    submission_data,
                    _id=submission_data["id"],
                    state=submission_data.get("state"),
                )
                for submission_data in submissions_data
            ]
        return []

    @staticmethod
    def build_submission_reports(submission_reports):
        if submission_reports is not None:
            return [
                SubmissionReport(submission_data, _id=submission_data["id"])
                for submission_data in submission_reports
            ]
        return []

    @staticmethod
    def build_file_objects(files_data):
        if files_data is not None:
            return [
                File(
                    submission_data,
                    name=submission_data["name"],
                    sha256=submission_data.get("sha256"),
                )
                for submission_data in files_data
            ]
        return []

    def build_incident_obj(self, raw_data: dict) -> IncidentData:
        """
        Builds Update Incident object
        Args:
            raw_data (dict): Raw API data item
        Returns:
            (Object): Filled Update Incident object
        """
        raw_data["data_type"] = "Incident"
        return IncidentData(raw_data=raw_data, message=raw_data.get("message", ""))

    @staticmethod
    def build_on_demand_scan_data(raw_json: SingleJson) -> OnDemandScanData:
        """Build a single OnDemandScanData object from an API response or a single scan
        JSON.
        Args:
            raw_json (SingleJson): Raw API data item

        Returns:
            OnDemandScanData: OnDemandScanData object.
        """
        resources = raw_json.get("resources", [])
        scan_data = resources[0] if resources else {}

        return OnDemandScanData(
            raw_json,
            resources=resources,
            scan_id=scan_data.get("id"),
            status=scan_data.get("status"),
            hosts=scan_data.get("hosts", []),
            host_groups=scan_data.get("host_groups", []),
            file_paths=scan_data.get("scan_inclusions", []),
            scan_exclusions=scan_data.get("scan_exclusions", []),
            cpu_priority=scan_data.get("cpu_priority"),
            cloud_ml_detection_level=scan_data.get("cloud_ml_level_detection"),
            cloud_ml_prevention_level=scan_data.get("cloud_ml_level_prevention"),
            sensor_ml_detection_level=scan_data.get("sensor_ml_level_detection"),
            sensor_ml_prevention_level=scan_data.get("sensor_ml_level_prevention"),
            created_on=scan_data.get("created_on"),
            updated_on=scan_data.get("updated_on"),
            description=scan_data.get("description"),
            endpoint_notification=scan_data.get("endpoint_notification"),
            quarantine=scan_data.get("quarantine", False),
            max_duration=scan_data.get("max_duration"),
            cid=scan_data.get("cid"),
        )

    def parse_search_events(self, raw_data: dict, job_id: str) -> SearchEventsData:
        return SearchEventsData.from_json(raw_data, job_id=job_id)

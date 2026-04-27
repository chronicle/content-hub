from __future__ import annotations
from .datamodels import *

SEVERITY_MAPPER = {
    "s0": {"label": "Info", "value": -1},
    "s1": {"label": "Low", "value": 40},
    "s2": {"label": "Medium", "value": 60},
    "s3": {"label": "High", "value": 80},
    "s4": {"label": "Critical", "value": 100},
    "s5": {"label": "Critical", "value": 100},
}
DEFAULT_API_SEVERITY = "s2"


class McAfeeMvisionEDRParser:
    @staticmethod
    def get_access_token(raw_json):
        return raw_json.get("access_token", "")

    @staticmethod
    def get_auth_token(raw_json):
        return raw_json.get("AuthorizationToken", "")

    def build_host_object(self, host_json):
        return Host(
            host_json,
            ma_guid=host_json.get("maGuid"),
            hostname=host_json.get("hostname"),
            desc=host_json.get("os", {}).get("desc"),
            last_boot_time=host_json.get("lastBootTime"),
            certainty=host_json.get("certainty"),
            net_interfaces=[
                self.build_net_interface_object(net_interface)
                for net_interface in host_json.get("netInterfaces", [])
            ],
        )

    def build_net_interface_object(self, net_interface_json):
        return NetInterface(net_interface_json, ip=net_interface_json.get("ip"))

    def build_task_response_object(self, response_json):
        return TaskResponseModel(
            response_json,
            status_id=response_json.get("id"),
            status=response_json.get("status"),
            location=response_json.get("location"),
            descriptions=[
                self.build_error_description_object(item)
                for item in response_json.get("items", [])
            ],
        )

    def build_error_description_object(self, response_json):
        return ErrorDescription(
            response_json, desc=response_json.get("errorDescription")
        )

    def build_siemplify_threat(self, threat_json):
        return Threat(
            raw_data=threat_json,
            threat_id=threat_json.get("id"),
            name=threat_json.get("name"),
            priority=SEVERITY_MAPPER.get(
                threat_json.get("severity", DEFAULT_API_SEVERITY)
            ).get("value"),
            threat_type=threat_json.get("type"),
            hashes=threat_json.get("hashes"),
            first_detected=threat_json.get("firstDetected"),
            last_detected=threat_json.get("lastDetected"),
        )

    def build_siemplify_detections_from_detections_response(self, detections_response):
        return [
            self.build_siemplify_detection(detection_json)
            for detection_json in detections_response.get("detections", [])
        ]

    def build_siemplify_detection(self, detection_json):
        return Detection(raw_data=detection_json)

    @staticmethod
    def build_case(case_data):
        # type: (dict) -> Case
        """
        Build Case object
        @param case_data: Case data from McAfee Mvision EDR API
        @return: Case object
        """
        return Case(
            raw_data=case_data,
            name=case_data.get("name"),
            summary=case_data.get("summary"),
            created=case_data.get("created"),
            owner=case_data.get("owner"),
            self_link=case_data.get("_links", {}).get("self", {}).get("href"),
            status_link=case_data.get("_links", {}).get("status", {}).get("href"),
            priority_link=case_data.get("_links", {}).get("priority", {}).get("href"),
            source=case_data.get("source"),
            is_automatic=case_data.get("isAutomatic"),
            last_modified=case_data.get("lastModified"),
            investigated=case_data.get("investigated"),
        )

    @staticmethod
    def build_task(task_data):
        # type: (dict) -> Task
        """
        Build Task object
        @param task_data: Task data from McAfee Mvision EDR API
        @return: Task object
        """
        return Task(
            raw_data=task_data,
            id=task_data.get("id"),
            status=task_data.get("status"),
            location=task_data.get("location"),
        )

    @staticmethod
    def build_task_status(task_status_data):
        # type: (dict) -> TaskStatus
        """
        Build Task status object
        @param task_status_data: Task status data from McAfee Mvision EDR API
        @return: Task status object
        """
        return TaskStatus(
            raw_data=task_status_data,
            id=task_status_data.get("id"),
            status=task_status_data.get("status"),
            success_host_responses=task_status_data.get("successHostResponses"),
            error_host_responses=task_status_data.get("errorHostResponses"),
        )

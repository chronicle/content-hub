from __future__ import annotations

import dataclasses
from typing import Optional

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class RubrikSecurityCloud:
    deployment_version: str = "8.0.0"
    token_response: Optional[SingleJson] = None
    cdm_cluster_location_response: Optional[SingleJson] = None
    cdm_cluster_connection_state_response: Optional[SingleJson] = None
    sonar_policy_objects_list_response: Optional[SingleJson] = None
    sonar_object_detail_response: Optional[SingleJson] = None
    ioc_scan_results_response: Optional[SingleJson] = None
    turbo_ioc_scan_response: Optional[SingleJson] = None
    list_events_response: Optional[SingleJson] = None
    list_object_snapshots_response: Optional[SingleJson] = None
    list_sonar_file_contexts_response: Optional[SingleJson] = None
    advanced_ioc_scan_response: Optional[SingleJson] = None

    def get_deployment_version(self) -> SingleJson:
        return {"data": {"deploymentVersion": self.deployment_version}}

    def set_token_response(self, token_data: SingleJson) -> None:
        self.token_response = token_data

    def get_token(self) -> SingleJson:
        if self.token_response:
            return self.token_response
        return {"access_token": "mock_access_token_12345", "expires_in": 1800}

    def get_cdm_cluster_location(self) -> SingleJson:
        if self.cdm_cluster_location_response:
            return self.cdm_cluster_location_response
        return {"data": {"clusterConnection": {"nodes": []}}}

    def get_cdm_cluster_connection_state(self) -> SingleJson:
        if self.cdm_cluster_connection_state_response:
            return self.cdm_cluster_connection_state_response
        return {"data": {"clusterConnection": {"nodes": []}}}

    def get_sonar_policy_objects_list(self) -> SingleJson:
        if self.sonar_policy_objects_list_response:
            return self.sonar_policy_objects_list_response
        return {"data": {"policyObjs": {"edges": []}}}

    def get_sonar_object_detail(self) -> SingleJson:
        if self.sonar_object_detail_response:
            return self.sonar_object_detail_response
        return {"data": {"policyObj": {}}}

    def get_ioc_scan_results(self) -> SingleJson:
        if self.ioc_scan_results_response:
            return self.ioc_scan_results_response
        return {"data": {"threatHuntDetailV2": {}, "threatHuntObjectMetrics": {}}}

    def get_turbo_ioc_scan(self) -> SingleJson:
        if self.turbo_ioc_scan_response:
            return self.turbo_ioc_scan_response
        return {"data": {"startTurboThreatHunt": {"huntId": "", "status": "PENDING"}}}

    def get_list_events(self) -> SingleJson:
        if self.list_events_response:
            return self.list_events_response
        return {
            "data": {
                "activitySeriesConnection": {
                    "edges": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

    def get_list_object_snapshots(self) -> SingleJson:
        if self.list_object_snapshots_response:
            return self.list_object_snapshots_response
        return {"data": {"snappableConnection": {"edges": []}}}

    def get_list_sonar_file_contexts(self) -> SingleJson:
        if self.list_sonar_file_contexts_response:
            return self.list_sonar_file_contexts_response
        return {
            "data": {
                "snapshotFilesDelta": {
                    "edges": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

    def get_advanced_ioc_scan(self) -> SingleJson:
        if self.advanced_ioc_scan_response:
            return self.advanced_ioc_scan_response
        return {"data": {"startBulkThreatHunt": {"huntId": "", "status": "PENDING"}}}

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

from crowd_strike_falcon.core.datamodels import (
    AlertDetails,
)
from TIPCommon.base.job.job_case import (
    CaseTagsData,
    JobAssigneeResult,
    JobCase,
    JobCommentsResult,
    JobSeverityResult,
    JobStatusResult,
    JobTagsResult,
    ProductTagsData,
)
from TIPCommon.data_models import AlertCard
from TIPCommon.types import SingleJson

from crowd_strike_falcon.tests.common import (
    MOCK_DATA,
    IdNotFoundError,
    check_for_invalid_elements,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from integration_testing import router
from integration_testing.common import create_case_details, get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class CrowdStrikeFalconSession(MockSession[MockRequest, MockResponse, CrowdStrikeFalcon]):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.add_comment_to_alert,
            self.get_alerts_details,
            self.get_detection_status,
            self.add_comment_to_detection,
            self.update_alert_detail,
            self.get_incidents_details,
            self.add_incident_comment,
            self.search_devices_ids,
            self.get_ioc_ids,
            self.delete_ioc_ids,
            self.contain_host_by_device_id,
            self.hide_host,
            self.get_update_action_external_sdk,
            self.get_devices,
            self.get_discover_streams,
            self.get_discover_streams_v1,
            self.get_api_external_sdk,
            self.get_action_external_sdk,
            self.get_device_combine,
            self.get_devices_entities_online_state,
            self.get_indicators_queries_devices,
            self.device_entities_devices,
            self.spotlight_queries_vulnerabilities,
            self.spotlight_entities_vulnerabilities_v2,
            self.spotlight_entities_remediations,
            self.get_iocs_entities_indicators_ids,
            self.patch_iocs_entities_indicators_ids,
            self.post_iocs_entities_indicators_ids,
            self.post_batch_init_session,
            self.post_batch_get_command_session,
            self.get_batch_get_command_session,
            self.real_time_response_entities_session,
            self.rtr_entities_command,
            self.get_rtr_entities_command,
            self.falconx_queries_submissions,
            self.get_falconx_entities_report_summaries,
            self.get_falconx_entities_submissions,
            self.falconx_entities_submissions,
            self.samples_entities_sample_v,
            self.real_time_response_entities_admin_command,
            self.get_rtr_entities_admin_command,
            self.ods_entities_scans,
            self.get_ods_entities_scans,
            self.get_alerts_queries_alerts,
            self.get_detects_queries_detects,
            self.get_incidents_queries_incidents,
            self.get_incidents_queries_behaviors,
            self.get_incidents_behaviors_details,
            self.initiate_search_job,
            self.get_search_job_results,
            self.get_user_uuids,
            self.search_users,
            self.get_active_scan_ids,
            self.get_hidden_devices_ids,
            get_oauth_token,
        ]

    @router.get("/users/queries/user-uuids/v1")
    def get_user_uuids(self, _: MockRequest) -> MockResponse:
        """Handles GET requests to /users/queries/user-uuids/v1."""
        return MockResponse(
            content={"resources": ["dummy_user_uuid"]},
            status_code=200,
        )

    @router.get("/user-management/queries/users/v1")
    def search_users(self, _: MockRequest) -> MockResponse:
        """Handles GET requests to /user-management/queries/users/v1."""
        return MockResponse(
            content={"resources": ["dummy_user_uuid"]},
            status_code=200,
        )

    @router.get("/incidents/queries/behaviors/v1")
    def get_incidents_queries_behaviors(self, _: MockRequest) -> MockResponse:
        incident_ids = list(self._product.list_items("incidents").keys())
        return MockResponse(content={"resources": incident_ids}, status_code=200)

    @router.get("/incidents/queries/incidents/v1")
    def get_incidents_queries_incidents(self, _: MockRequest) -> MockResponse:
        incident_ids = list(self._product.list_items("incidents").keys())
        return MockResponse(content={"resources": incident_ids}, status_code=200)

    @router.get("/detects/queries/detects/v1")
    def get_detects_queries_detects(self, _: MockRequest) -> MockResponse:
        detection_ids = list(self._product.list_items("detections").keys())
        return MockResponse(content={"resources": detection_ids}, status_code=200)

    @router.get("/alerts/queries/alerts/v2")
    def get_alerts_queries_alerts(self, _: MockRequest) -> MockResponse:
        alert_ids = list(self._product.list_items("alerts").keys())
        return MockResponse(content={"resources": alert_ids}, status_code=200)

    @router.get("/ods/entities/scans/v1")
    def get_ods_entities_scans(self, _: MockRequest) -> MockResponse:
        """Handles GET requests to /ods/entities/scans/v1.

        Returns a MockResponse containing a list of on-demand scan resources.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing the on-demand scan resources.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_on_demand_scans(
                        on_demand_scan,
                    ).to_json()["resources"][0]
                    for on_demand_scan, _ in self._product.list_items(
                        "on_demand_scans",
                    ).items()
                ],
            },
            status_code=200,
        )

    @router.post("/ods/entities/scans/v1")
    def ods_entities_scans(self, _: MockRequest) -> MockResponse:
        """Handles POST requests to /ods/entities/scans/v1.

        Returns a MockResponse containing a list of on-demand scan resources.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing the on-demand scan resources.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_on_demand_scans(on_demand_scan).to_json()
                    for on_demand_scan, _ in self._product.list_items(
                        "on_demand_scans",
                    ).items()
                ],
            },
            status_code=200,
        )

    @router.get("/real-time-response/entities/admin-command/v1")
    def get_rtr_entities_admin_command(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.post("/real-time-response/entities/admin-command/v1")
    def real_time_response_entities_admin_command(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.post("/samples/entities/samples/v2/")
    def samples_entities_sample_v(self, _: MockRequest) -> MockResponse:
        """Handles POST requests to /samples/entities/samples/v2/.

        Returns a MockResponse containing a list of file resources.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing the file resources.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_file(file)[0].to_json()
                    for file, _ in self._product.list_items("files").items()
                ],
            },
            status_code=200,
        )

    @router.get("/falconx/entities/submissions/v1/")
    def get_falconx_entities_submissions(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=MOCK_DATA["get_falconx_entities_submissions"],
            status_code=200,
        )

    @router.get("/falconx/entities/report-summaries/v1/")
    def get_falconx_entities_report_summaries(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=MOCK_DATA["get_falconx_entities_report_summaries"],
            status_code=200,
        )

    @router.get("/falconx/queries/submissions/v1")
    def falconx_queries_submissions(self, _: MockRequest) -> MockResponse:
        """Handles GET requests to /falconx/queries/submissions/v1.

        Retrieves a list of Falcon X submission reports.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing a list of submission report
                          resources. Returns a 200 status code.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_submission_report(submission_report_id).to_json()
                    for submission_report_id in
                    self._product.list_items("submission_reports")
                ],
            },
            status_code=200,
        )

    @router.post("/falconx/entities/submissions/v1")
    def falconx_entities_submissions(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=MOCK_DATA["falconx_entities_submissions"],
            status_code=200,
        )

    @router.get("/real-time-response/entities/active-responder-command/v1")
    def get_rtr_entities_command(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=MOCK_DATA[
                "get_real_time_response_entities_active_responder_command"
            ],
            status_code=200,
        )

    @router.post("/real-time-response/entities/active-responder-command/v1")
    def rtr_entities_command(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=MOCK_DATA["real_time_response_entities_active_responder_command"],
            status_code=200,
        )

    @router.post("/real-time-response/entities/sessions/v1")
    def real_time_response_entities_session(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=MOCK_DATA["real_time_response_entities_session"],
            status_code=200,
        )

    @router.post("/real-time-response/combined/batch-init-session/v1")
    def post_batch_init_session(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=MOCK_DATA["post_batch_init_session"],
            status_code=200,
        )

    @router.post("/real-time-response/combined/batch-get-command/v1")
    def post_batch_get_command_session(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content=MOCK_DATA["post_batch_get_command_session"],
            status_code=200,
        )

    @router.get("/real-time-response/combined/batch-get-command/v1")
    def get_batch_get_command_session(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.post("/iocs/entities/indicators/v1")
    def post_iocs_entities_indicators_ids(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.patch("/iocs/entities/indicators/v1")
    def patch_iocs_entities_indicators_ids(self, _: MockRequest) -> MockResponse:
        """Handles PATCH requests to /iocs/entities/indicators/v1.

        Updates custom indicators and retrieves their details.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing a list of updated custom indicator
                          resources. Returns a 200 status code.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_custom_indicators(indicator_value).to_json()
                    for indicator_value in
                    self._product.list_items("custom_indicators").keys()
                ],
            },
            status_code=200,
        )

    @router.get("/iocs/entities/indicators/v1")
    def get_iocs_entities_indicators_ids(self, _: MockRequest) -> MockResponse:
        """Handles GET requests to /iocs/entities/indicators/v1.

        Retrieves a list of custom indicators.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing a list of custom indicator
                          resources. Returns a 200 status code.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_custom_indicators(indicator_value).to_json()
                    for indicator_value in
                    self._product.list_items("custom_indicators").keys()
                ],
            },
            status_code=200,
        )

    @router.get("/spotlight/entities/remediations/v2")
    def spotlight_entities_remediations(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.get("/spotlight/entities/vulnerabilities/v2")
    def spotlight_entities_vulnerabilities_v2(self, _: MockRequest) -> MockResponse:
        """Handles GET requests to /spotlight/entities/vulnerabilities/v2.

        Retrieves a list of vulnerabilities.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing a list of vulnerability resources.

        """
        resources = [
            self._product.get_vulnerability(device).to_json()
            for device in self._product.list_items("vulnerabilities")
        ]
        return MockResponse(content={"resources": resources}, status_code=200)

    @router.get("/spotlight/queries/vulnerabilities/v1")
    def spotlight_queries_vulnerabilities(self, _: MockRequest) -> MockResponse:
        vulnerability_ids = list(self._product.list_items("vulnerabilities").keys())
        return MockResponse(content={"resources": vulnerability_ids}, status_code=200)

    @router.patch("/alerts/entities/alerts/v3")
    def add_comment_to_alert(self, request: MockRequest) -> MockResponse:
        """Adds a comment to an alert based on the provided request payload.

        Args:
            request (MockRequest): The incoming request object containing the payload.

        Returns:
            MockResponse: A response object indicating success or failure.

        Raises:
            None: This method handles all exceptions internally by returning
                appropriate responses.

        """
        json_data: dict = get_request_payload(request, ["json"])

        error_response = check_for_invalid_elements(json_data)
        if error_response:
            return MockResponse(content=error_response, status_code=400)

        alert_ids: list[str] = json_data.get("composite_ids") or json_data.get("ids")
        if alert_ids:
            alerts: list[AlertDetails] = list(self._product.list_items("alerts"))
            for alert in alerts:
                try:
                    self._product.update_alert(
                        alert,
                        comments=json_data.get("action_parameters")[0]["value"],
                    )
                except IdNotFoundError:
                    return MockResponse(content={}, status_code=404)

        return MockResponse(content={}, status_code=200)

    @router.post("/alerts/entities/alerts/v2")
    def get_alerts_details(self, request: MockRequest) -> MockResponse:
        """Retrieves details of alerts based on the provided request payload.

        Args:
            request (MockRequest): The incoming request object containing the payload.

        Returns:
            MockResponse: A response object containing the details of the alerts if
                the request is valid. Returns an error response if the request payload
                contains invalid IDs.

        Raises:
            None: All errors are handled internally by returning appropriate responses.

        """
        json_data = get_request_payload(request, ["json"])

        error_response = check_for_invalid_elements(json_data)
        if error_response:
            return MockResponse(content=error_response, status_code=400)

        return MockResponse(content=MOCK_DATA["get_alerts_details"], status_code=200)

    @router.post("/detects/entities/summaries/GET/v1")
    def get_detection_status(self, request: MockRequest) -> MockResponse:
        """Retrieves the status of detections based on the provided request payload.

        Args:
            request (MockRequest): The incoming request object containing the payload.

        Returns:
            MockResponse: A response object containing the detection status details if
                the request is valid. Returns an error response if the request payload
                contains invalid IDs.

        Raises:
            None: All errors are handled internally by returning appropriate responses.

        """
        json_data = get_request_payload(request, ["json"])

        error_response = check_for_invalid_elements(json_data)
        if error_response:
            return MockResponse(content=error_response, status_code=400)

        return MockResponse(content=MOCK_DATA["get_detection_status"], status_code=200)

    @router.patch("/detects/entities/detects/v2")
    def add_comment_to_detection(self, request: MockRequest) -> dict[str, list[
        dict[str, str | int]]] | MockResponse:
        """Adds a comment to a detection based on the provided request payload.

        Args:
            request (MockRequest): The incoming request object containing the payload.

        Returns:
            MockResponse: A response object indicating success or failure.
                Returns an error response if the request payload contains invalid IDs.

        Raises:
            None: All errors are handled internally by returning appropriate responses.

        """
        json_data = get_request_payload(request, ["json"])

        error_response = check_for_invalid_elements(json_data)
        if error_response:
            return MockResponse(content=error_response, status_code=400)

        return MockResponse(content={}, status_code=200)

    @router.patch("/alerts/entities/alerts/v2/")
    def update_alert_detail(self, request: MockRequest) -> MockResponse:
        """Handles PATCH requests to /alerts/entities/alerts/v2/.

        Updates alert details based on the provided request payload.

        Args:
            request: The incoming request object containing the payload.

        Returns:
            A MockResponse containing the updated alert details.

        """
        json_data: dict = get_request_payload(request, ["json"])
        detection_id: str = json_data["ids"][0]

        return MockResponse(
            content=self._product.get_detection(detection_id).to_json(),
            status_code=200,
        )

    @router.post("/incidents/entities/incidents/GET/v1")
    def get_incidents_details(self, request: MockRequest) -> MockResponse:
        """Retrieves details of incidents based on the provided request payload.

        Args:
            request (MockRequest): The incoming request object containing the payload.

        Returns:
            MockResponse: A response object containing the incident details
                if the request is valid. Returns an error response
                if the request payload contains invalid IDs.

        Raises:
            None: All errors are handled internally by returning appropriate responses.

        """
        json_data = get_request_payload(request, ["json"])

        error_response = check_for_invalid_elements(json_data)
        if error_response:
            return MockResponse(content=error_response, status_code=400)

        return MockResponse(
            content={
                "resources": [
                    self._product.get_incident(key).to_json()
                    for key in json_data["ids"]
                ],
            },
            status_code=200,
        )

    @router.post("/incidents/entities/behaviors/GET/v1")
    def get_incidents_behaviors_details(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.post("/incidents/entities/incident-actions/v1")
    def add_incident_comment(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.get("/devices/queries/devices/v1")
    def search_devices_ids(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=MOCK_DATA["search_devices_ids"], status_code=200)

    @router.get("/iocs/queries/indicators/v1")
    def get_ioc_ids(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=MOCK_DATA["get_ioc_ids"], status_code=200)

    @router.delete("/iocs/entities/indicators/v1")
    def delete_ioc_ids(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.get("/devices/entities/devices/v2")
    def get_devices(self, _: MockRequest) -> MockResponse:
        """Handles GET requests to /devices/entities/devices/v2.

        Retrieves all available device details.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing a list of device resources.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_device(device).to_json()
                    for device in self._product.list_items("devices")
                ],
            },
            status_code=200,
        )

    @router.post("/devices/entities/devices/v2")
    def device_entities_devices(self, _: MockRequest) -> MockResponse:
        """Handles POST requests to /devices/entities/devices/v2.

        Retrieves device details for a list of device IDs provided in the request body.
        While this endpoint uses POST, it effectively functions similarly to a GET
        request with a body.  This is common for retrieving details for multiple items
        in CrowdStrike's API.

        Args:
            _ (MockRequest): The incoming request object.  The body is expected
                             to contain a list of device IDs, but this mock
                             implementation currently retrieves all devices
                             regardless of the request body.

        Returns:
            MockResponse: A MockResponse containing a list of device resources.
                           Returns a 200 status code.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_device(device).to_json()
                    for device in self._product.list_items("devices")
                ],
            },
            status_code=200,
        )

    @router.get("/sensors/entities/datafeed/v2")
    def get_discover_streams(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "resources": [{
                    "dataFeedURL": "/sensors/entities/datafeed/v1/0",
                }],
            },
            status_code=200,
        )

    @router.get("/sensors/entities/datafeed/v1/0")
    def get_discover_streams_v1(self, _: MockRequest) -> MockResponse:
        detections = list(self._product.list_items("stream_detections").values())
        content = detections[0].to_json() if detections else {}
        return MockResponse(content=content, status_code=200)

    @router.post("/devices/entities/devices-actions/v2")
    def contain_host_by_device_id(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.post("/devices/entities/devices-actions/v2")
    def hide_host(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.post("/devices/combined/devices/login-history/v1")
    def get_device_combine(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.get("/devices/entities/online-state/v1")
    def get_devices_entities_online_state(self, request: MockRequest) -> MockResponse:
        """Handles GET requests to /devices/entities/online-state/v1.

        Retrieves the online state of devices based on the provided IDs in the
            request parameters.

        Args:
            request: The incoming request object containing the device IDs
                in the parameters.

        Returns:
            A MockResponse containing the online state of the requested devices.

        """
        json_data = get_request_payload(request, ["params"])

        return MockResponse(
            content={
                "resources": [
                    {
                        "id": json_data["ids"][0],
                        "state": "online",
                    },
                ],
            },
            status_code=200,
        )

    @router.post("/api/external/v1/sdk/CreateCaseInsight")
    def get_api_external_sdk(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={})

    @router.post("/api/external/v1/sdk/AlertFullDetails")
    def get_action_external_sdk(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={})

    @router.post("/api/external/v1/sdk/UpdateEntities")
    def get_update_action_external_sdk(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={})

    @router.get("/indicators/queries/devices/v1")
    def get_indicators_queries_devices(self, _: MockRequest) -> MockResponse:
        """Handles GET requests to /indicators/queries/devices/v1.

        Returns a MockResponse containing a list of device resources associated
            with indicators.

        Args:
            _ (MockRequest): The incoming request object (unused).

        Returns:
            MockResponse: A MockResponse containing the device resources.

        """
        return MockResponse(
            content={
                "resources": [
                    self._product.get_device(device).to_json()
                    for device in self._product.list_items("devices").keys()
                ],
            },
            status_code=200,
        )

    @router.post(r"/humio/api/v1/repositories/[a-z0-9_\-]+/queryjobs")
    def initiate_search_job(self, _: MockRequest) -> MockResponse:
        """Handles POST request to /humio/api/v1/repositories/"""
        return MockResponse(
            content={
                "hashedQueryOnView": "4cc4158a",
                "id": "P0-someJobId",
            },
            status_code=200,
        )

    @router.get(r"/humio/api/v1/repositories/[a-z0-9_\-]+/queryjobs/[a-zA-Z0-9\-]+")
    def get_search_job_results(self, request: MockRequest) -> MockResponse:
        """Handles GET request to /humio/api/v1/repositories/"""
        job_id: str = request.url.path.split("/")[-1]
        key: str = (
            "no_results" if "investigate_view" in request.url.path else "with_results"
        )
        simulated_raw_data: SingleJson = MOCK_DATA[key]
        self._product.add_events(simulated_raw_data, job_id)
        search_data = self._product.get_events(job_id)

        return MockResponse(
            content={
                "cancelled": search_data.cancelled,
                "done": search_data.done,
                "events": search_data.events,
            },
            status_code=200,
        )

    @router.get("/ods/queries/scans/v1")
    def get_active_scan_ids(self, _: MockRequest) -> MockResponse:
        scan_ids = list(self._product.list_items("on_demand_scans").keys())
        return MockResponse(content={"resources": scan_ids}, status_code=200)

    @router.get("/devices/queries/devices-hidden/v1")
    def get_hidden_devices_ids(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={"resources": []}, status_code=200)


@router.post("/oauth2/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Simulates an OAuth token generation endpoint.

    Args:
        request (MockRequest): The incoming request object containing the payload.

    Returns:
        MockResponse: A response object containing either an OAuth token or
            an error message.

    Raises:
        None: All errors are handled internally by returning appropriate responses.

    """
    if "raise_error" in request.kwargs["data"].values():
        return MockResponse(
            content={
                "meta": {
                    "query_time": 1.86e-7,
                    "powered_by": "crowdstrike-api-gateway",
                    "trace_id": "f7be6527-81a1-4fa4-be88-54d6781ca3c4",
                },
                "errors": [
                    {
                        "code": 401,
                        "message": "access denied, authorization failed",
                    },
                ],
            },
            status_code=400,
        )

    return MockResponse(
        content={
            "access_token": "1000.ac445cfb678764b9da88ac5024b767c5.ac445cfb6724b76",
            "expires_in": 999_999_999_999,
            "token_type": "Bearer",
            "ext_expires_in": 999_999_999_999,
        },
        headers={"content-type": "application/json"},
    )


class MockJobCase(JobCase):
    def __init__(self, case_id: str, ticket_id: str = "valid_composite_id") -> None:
        from TIPCommon.data_models import CaseDetails
        alert = AlertCard.from_json(
            {
                "identifier": "alert_1",
                "ticketId": ticket_id,
                "status": 1,
                "priority": 40,
            },
        )
        case_detail = CaseDetails.from_json({"id": 1, "name": case_id})
        case_detail.alerts = [alert]
        super().__init__(case_detail=case_detail, modification_time=0)
        self.case_comments = []

    def add_product_incident(self, incident, product_key):
        pass

    def get_alert_identifier_from_product_id(self, product_id):
        return "alert_1"

    def get_comments_to_sync(self, *_args, **_kwargs):
        return JobCommentsResult(product_comments_sync_to_case=[], case_comments_sync_to_product=[])

    def get_tags_to_sync(self, *_args, **_kwargs):
        return JobTagsResult(
            product_tags_sync_to_case=ProductTagsData([], []),
            case_tags_sync_to_product=CaseTagsData([], []),
        )

    def get_severity_to_sync(self, *_args, **_kwargs):
        return JobSeverityResult(updates=[])

    def get_assignee_to_sync(self, *_args, **_kwargs):
        return JobAssigneeResult(target_user=None, alert=None)

    def get_status_to_sync(self, *_args, **_kwargs):
        return JobStatusResult(alerts_to_close_in_soar=[], incidents_to_close_in_product=[])


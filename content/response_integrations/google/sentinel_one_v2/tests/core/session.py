import copy
import re
import requests

from TIPCommon.base.job.job_case import (
    JobCase,
    JobCommentsResult,
    JobTagsResult,
    ProductTagsData,
    CaseTagsData,
    JobSeverityResult,
    JobAssigneeResult,
    JobStatusResult,
)
from TIPCommon.data_models import AlertCard
from TIPCommon.types import SingleJson

from sentinel_one_v2.tests.common import MOCK_QUERY_STATUS
from sentinel_one_v2.tests.core.product import SentinelOneV2
from integration_testing import router
from integration_testing.common import create_case_details
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class SentinelOneV2Session(MockSession[MockRequest, MockResponse, SentinelOneV2]):
    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.get_agent_count,
            self.get_sites,
            self.get_agents,
            self.init_query,
            self.get_query_status,
            self.get_events_process,
            self.get_cloud_detection_alerts,
            self.update_cloud_detection_alert_incident_status,
            self.update_cloud_detection_alert_verdict,
            self.get_activities,
            self.get_threats,
            self.search_cases,
            self.update_threat_incident,
            self.add_threat_notes,
            self.get_threat_notes,
            self.disconnect_agent,
            self.reconnect_agent,
            self.initiate_full_scan,
            self.get_agent_applications,
            self.get_hash_reputation,
            self.get_system_status,
            self.get_db_system_status,
            self.get_cache_system_status,
            self.get_system_info,
            self.get_restrictions,
            self.post_restrictions,
            self.delete_restrictions,
            self.post_exclusions,
            self.get_groups,
            self.mitigate_threat,
            self.mark_as_threat_verdict,
            self.move_agents,
            self.fetch_file,
            self.get_timeline,
            self.get_device_control,
            self.post_device_control,
            self.delete_device_control,
            self.put_device_control,
            self.mark_as_resolved,
            self.get_dv_events,
        ]

    @router.get(r"/web/api/v2\.\d+/agents/count")
    def get_agent_count(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(status_code=200, content={"data": {"total": 7}})

    @router.get("/web/api/v2.1/sites")
    def get_sites(self, request: MockRequest) -> MockResponse:
        """Returns a site that matches the site name."""
        site_name: str = request.kwargs.get("params", {}).get("name")
        site_response: SingleJson = self._product.get_site_by_name(site_name)
        return MockResponse(content=site_response, status_code=200)

    @router.get("/web/api/v2.1/agents")
    def get_agents(self, request: MockRequest) -> MockResponse:
        """Returns agents that match the site ID or computer name."""
        if self._product.simulate_api_error:
            return MockResponse(
                status_code=500,
                content={"error": "Simulated API Error"},
            )

        params = request.kwargs.get("params", {})
        if "siteIds" in params:
            site_id: str = params["siteIds"]
            agents_response: SingleJson = self._product.get_agents_by_site(
                site_ids=site_id, limit=params.get("limit")
            )
            return MockResponse(content=agents_response, status_code=200)

        if "computerName" in params:
            computer_name: str = params.get("computerName")
            try:
                mock_agent: SingleJson = self._product.get_agent(computer_name)
                return MockResponse(content=mock_agent, status_code=200)
            except KeyError:
                return MockResponse(content={"data": []}, status_code=200)

        return MockResponse(content={"data": []}, status_code=200)

    @router.post(r"/web/api/v2\.\d+/dv/init-query")
    def init_query(self, request: MockRequest) -> MockResponse:
        """Returns init query response to the integration"""
        agent_uuid: str = request.kwargs.get("json").get("query")
        agent_uuid: str = re.findall(r"\d+", agent_uuid)[0]
        init_response: SingleJson = self._product.get_init_response_by_uuid(agent_uuid)
        return MockResponse(content=init_response, status_code=200)

    @router.get(r"/web/api/v2\.\d+/dv/query-status")
    def get_query_status(self, _: MockRequest) -> MockResponse:
        """Returns the status of the query"""
        response_mock_query_status: SingleJson = copy.deepcopy(MOCK_QUERY_STATUS)
        if self._product.get_query_status_calls() == 1:
            response_mock_query_status.update(
                {"progressStatus": 0, "responseState": "RUNNING"}
            )
            self._product.increment_query_status_calls()

        return MockResponse(content=response_mock_query_status, status_code=200)

    @router.get("/web/api/v2.1/dv/events/process")
    def get_events_process(self, request: MockRequest) -> MockResponse:
        """Returns the events process"""
        agent_uuid: str = request.kwargs.get("params").get("queryId")
        response: SingleJson = self._product.get_final_response_by_uuid(agent_uuid)
        return MockResponse(content=response, status_code=200)

    @router.get("/web/api/v2.1/cloud-detection/alerts")
    def get_cloud_detection_alerts(self, request: MockRequest) -> MockResponse:
        """Returns cloud detection alerts that match the ids."""
        params = request.kwargs.get("params", {})
        alert_ids: list[str] = params.get("ids", "").split(",")
        found_alerts: list[SingleJson] = []
        for alert_id in alert_ids:
            try:
                alert = self._product.get_cloud_detection_alert(alert_id)
                found_alerts.append(alert.to_json())
            except KeyError:
                continue

        return MockResponse(content={"data": found_alerts}, status_code=200)

    @router.post("/web/api/v2.1/cloud-detection/alerts/incident")
    def update_cloud_detection_alert_incident_status(
        self, request: MockRequest
    ) -> MockResponse:
        """Updates the incident status of cloud detection alerts."""
        alert_ids: list[str] = (
            request.kwargs.get("json", {}).get("filter", {}).get("ids", [])
        )
        status: str = (
            request.kwargs.get("json", {}).get("data", {}).get("incidentStatus")
        )

        for alert_id in alert_ids:
            alert = self._product.get_cloud_detection_alert(alert_id)
            alert.incident_status = status

        return MockResponse(
            content={"data": {"affected": len(alert_ids)}}, status_code=200
        )

    @router.post("/web/api/v2.1/cloud-detection/alerts/analyst-verdict")
    def update_cloud_detection_alert_verdict(
        self, request: MockRequest
    ) -> MockResponse:
        """Updates the analyst verdict of cloud detection alerts."""
        alert_ids: list[str] = (
            request.kwargs.get("json", {}).get("filter", {}).get("ids", [])
        )
        verdict: str = (
            request.kwargs.get("json", {}).get("data", {}).get("analystVerdict")
        )

        for alert_id in alert_ids:
            alert = self._product.get_cloud_detection_alert(alert_id)
            alert.verdict = verdict

        return MockResponse(
            content={"data": {"affected": len(alert_ids)}}, status_code=200
        )

    @router.get("/web/api/v2.1/activities")
    def get_activities(self, request: MockRequest) -> MockResponse:
        """Returns activities that match filters."""
        params = request.kwargs.get("params", {})
        filtered_activities = []

        threat_ids = (
            params.get("threatIds", "").split(",") if "threatIds" in params else []
        )
        created_at_gte = params.get("createdAt__gte")

        for activity in self._product.activities:
            if threat_ids and str(activity.get("threatId")) not in threat_ids:
                continue
            if (
                created_at_gte
                and activity.get("createdAt")
                and activity.get("createdAt") < created_at_gte
            ):
                continue
            filtered_activities.append(activity)

        return MockResponse(content={"data": filtered_activities}, status_code=200)

    @router.get(r"/web/api/v2\.\d+/threats")
    def get_threats(self, request: MockRequest) -> MockResponse:
        """Returns threats that match the ids."""
        if self._product.simulate_transient_error:
            self._product.simulate_transient_error = False
            raise requests.exceptions.ConnectionError("Transient error")

        params = request.kwargs.get("params", {})
        ids = params.get("ids", "").split(",")
        found_threats = []
        for tid in ids:
            if tid in self._product.threats:
                found_threats.append(self._product.threats[tid])
        return MockResponse(content={"data": found_threats}, status_code=200)

    @router.post(r"/web/api/v2\.\d+/threats/incident")
    def update_threat_incident(self, request: MockRequest) -> MockResponse:
        """Simulates updating threat incident status."""
        payload = request.kwargs.get("json", {})
        data = payload.get("data", {})
        ids = payload.get("filter", {}).get("ids", [])
        status = data.get("incidentStatus")

        affected = 0
        for tid in ids:
            if tid in self._product.threats:
                self._product.threats[tid]["incidentStatus"] = status
                affected += 1

        return MockResponse(content={"data": {"affected": affected}}, status_code=200)

    @router.post(r"/web/api/v2\.\d+/threats/notes")
    def add_threat_notes(self, request: MockRequest) -> MockResponse:
        """Simulates adding notes to threat."""
        payload = request.kwargs.get("json", {})
        data = payload.get("data", {})
        ids = payload.get("filter", {}).get("ids", [])
        text = data.get("text")

        affected = 0
        for tid in ids:
            if tid in self._product.threats:
                if "notes" not in self._product.threats[tid]:
                    self._product.threats[tid]["notes"] = []
                self._product.threats[tid]["notes"].append(text)
                affected += 1

        return MockResponse(content={"data": {"affected": affected}}, status_code=200)

    @router.get(r"/web/api/v2\.\d+/threats/.*/notes")
    def get_threat_notes(self, request: MockRequest) -> MockResponse:
        """Returns notes for a threat."""
        path = request.url.path
        parts = path.split("/")
        threat_id = parts[-2]
        notes = []
        if threat_id in self._product.threats:
            notes = self._product.threats[threat_id].get("notes", [])

        formatted_notes = [{"text": note} for note in notes]
        return MockResponse(content={"data": formatted_notes}, status_code=200)

    @router.post("/api/external/v1/search/CaseSearchEverything")
    def search_cases(self, _request: MockRequest) -> MockResponse:
        """Returns empty list of cases for now."""
        return MockResponse(content={"results": []}, status_code=200)



    # ------------------------------------------------------------------ #
    # Routes added for the new test suite                                  #
    # ------------------------------------------------------------------ #

    @router.post("/web/api/v2.1/agents/actions/disconnect")
    def disconnect_agent(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"affected": 1}}, status_code=200)

    @router.post("/web/api/v2.1/agents/actions/connect")
    def reconnect_agent(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"affected": 1}}, status_code=200)

    @router.post("/web/api/v2.1/agents/actions/initiate-scan")
    def initiate_full_scan(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"affected": 1}}, status_code=200)

    @router.get("/web/api/v2.1/agents/applications")
    def get_agent_applications(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": [{"name": "TestApp", "publisher": "ACME", "size": 1024, "version": "1.0"}]},
            status_code=200,
        )

    @router.get(r"/web/api/v2.1/hashes/.*/reputation")
    def get_hash_reputation(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": {"rank": 7, "hash": "abc123"}},
            status_code=200,
        )

    @router.get("/web/api/v2.1/system/status")
    def get_system_status(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"health": "ok"}}, status_code=200)

    @router.get("/web/api/v2.1/system/status/db")
    def get_db_system_status(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={"data": {"health": "ok"}}, status_code=200)

    @router.get("/web/api/v2.1/system/status/cache")
    def get_cache_system_status(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={"data": {"health": "ok"}}, status_code=200)

    @router.get("/web/api/v2.1/system/info")
    def get_system_info(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": {"latestAgentVersion": "24.1.4.257", "buildVersion": "24.1"}},
            status_code=200,
        )

    @router.get("/web/api/v2.1/restrictions")
    def get_restrictions(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": [
                {"id": "bl_001", "type": "black_hash", "value": "aaabbbccc",
                 "createdAt": "2024-01-01T00:00:00Z"},
            ]},
            status_code=200,
        )

    @router.post("/web/api/v2.1/restrictions")
    def post_restrictions(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": [
                {"id": "bl_new", "type": "black_hash", "value": "aaabbbccc",
                 "createdAt": "2024-01-01T00:00:00Z"},
            ]},
            status_code=200,
        )

    @router.delete("/web/api/v2.1/restrictions")
    def delete_restrictions(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"affected": 1}}, status_code=200)

    @router.post("/web/api/v2.1/exclusions")
    def post_exclusions(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": [
                {"id": "excl_001", "type": "white_hash", "value": "aaabbbccc",
                 "createdAt": "2024-01-01T00:00:00Z"},
            ]},
            status_code=200,
        )

    @router.get("/web/api/v2.1/groups")
    def get_groups(self, request: MockRequest) -> MockResponse:
        """Return groups, filtered by name if provided."""
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        params = request.kwargs.get("params", {})
        name = params.get("name")
        if name == "TestGroup":
            return MockResponse(
                content={"data": [{"id": "g_001", "name": "TestGroup", "type": "static", "rank": None}]},
                status_code=200,
            )
        return MockResponse(content={"data": []}, status_code=200)

    @router.post(r"/web/api/v2.1/threats/mitigate/.*")
    def mitigate_threat(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"affected": 1}}, status_code=200)

    @router.post("/web/api/v2.1/threats/analyst-verdict")
    def mark_as_threat_verdict(self, request: MockRequest) -> MockResponse:
        """Update the analyst verdict for a set of threat IDs."""
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        payload = request.kwargs.get("json", {})
        ids = payload.get("filter", {}).get("ids", [])
        verdict = payload.get("data", {}).get("analystVerdict")
        for tid in ids:
            if tid in self._product.threats:
                ti = self._product.threats[tid]
                if "threatInfo" not in ti:
                    ti["threatInfo"] = {}
                ti["threatInfo"]["analystVerdict"] = verdict
        return MockResponse(content={"data": {"affected": len(ids)}}, status_code=200)

    @router.put(r"/web/api/v2.1/groups/.*/move-agents")
    def move_agents(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"agentsMoved": 1}}, status_code=200)

    @router.post("/web/api/v2.1/threats/fetch-file")
    def fetch_file(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"affected": 1}}, status_code=200)

    @router.get(r"/web/api/v2.1/threats/.*/timeline")
    def get_timeline(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": []},
            status_code=200,
        )

    @router.get("/web/api/v2.1/device-control")
    def get_device_control(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": [{"id": "dc_001", "ruleName": "TestRule", "status": "Enabled"}]},
            status_code=200,
        )

    @router.post("/web/api/v2.1/device-control")
    def post_device_control(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": {"id": "dc_new", "ruleName": "NewRule", "status": "Enabled"}},
            status_code=200,
        )

    @router.delete(r"/web/api/v2.1/device-control/.*")
    def delete_device_control(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(content={"data": {"affected": 1}}, status_code=200)

    @router.put(r"/web/api/v2.1/device-control/.*")
    def put_device_control(self, _: MockRequest) -> MockResponse:
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        return MockResponse(
            content={"data": {"id": "dc_001", "ruleName": "UpdatedRule", "status": "Enabled"}},
            status_code=200,
        )

    @router.post("/web/api/v2.1/threats/mark-as-resolved")
    def mark_as_resolved(self, request: MockRequest) -> MockResponse:
        """Mark a set of threats as resolved."""
        if self._product.simulate_api_error:
            return MockResponse(status_code=500, content={"error": "Simulated API Error"})
        payload = request.kwargs.get("json", {})
        ids = payload.get("filter", {}).get("ids", [])
        for tid in ids:
            if tid in self._product.threats:
                ti = self._product.threats[tid]
                if "threatInfo" not in ti:
                    ti["threatInfo"] = {}
                ti["threatInfo"]["incidentStatus"] = "resolved"
        return MockResponse(content={"data": {"affected": len(ids)}}, status_code=200)

    @router.get(r"/web/api/v2\.\d+/dv/events")
    def get_dv_events(self, request: MockRequest) -> MockResponse:
        """Returns DV query events (used by GetDeepVisibilityQueryResult)."""
        params = request.kwargs.get("params", {})
        query_id: str = params.get("queryId", "")
        try:
            response: SingleJson = self._product.get_final_response_by_uuid(query_id)
        except KeyError:
            response = {"data": []}
        return MockResponse(content=response, status_code=200)

class MockJobCase(JobCase):
    def __init__(self, case_id: str) -> None:
        alert = AlertCard.from_json(
            {
                "identifier": "alert_1",
                "ticketId": "123456789012345678",
                "status": 1,
                "priority": 40,
            }
        )
        case_detail = create_case_details(id_=1, name=case_id, alerts=[alert])
        super().__init__(case_detail=case_detail, modification_time=0)
        self.case_comments = []

    # pylint: disable=unused-argument
    def add_product_incident(self, incident, product_key):
        pass

    # pylint: disable=unused-argument
    def get_alert_identifier_from_product_id(self, product_id):
        return "alert_1"

    def get_comments_to_sync(self, *_args, **_kwargs):
        return JobCommentsResult(
            product_comments_sync_to_case=[], case_comments_sync_to_product=[]
        )

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
        return JobStatusResult(
            alerts_to_close_in_soar=[], incidents_to_close_in_product=[]
        )

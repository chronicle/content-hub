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

import json
import re
from collections.abc import Iterable

from TIPCommon.types import SingleJson

from microsoft_defender_atp.core.datamodels import Alert
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class MicrosoftDefenderATPSession(
    MockSession[MockRequest, MockResponse, MicrosoftDefenderATP],
):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.generate_token,
            # More-specific routes must precede broader ones so the router
            # matches them first.
            self.get_machine_vulnerabilities,
            self.get_machine_recommendations,
            self.get_machine_logon_users,
            self.get_machine_related_alerts,
            self.isolate_machine,
            self.unisolate_machine,
            self.run_antivirus_scan,
            self.stop_and_quarantine_file,
            self.run_live_response,
            self.get_machine_actions,
            self.get_file_related_alerts,
            self.get_file_related_machines,
            self.get_file_info,
            self.get_file_stats,
            self.run_advanced_hunting_query,
            self.get_alerts_or_test_connectivity,
            self.get_machines,
            self.get_indicators,
            self.submit_indicator,
            self.delete_indicator,
            self.update_alert,
            self.get_live_response_status,
            self.get_user_related_alerts,
            self.siemplify_internal_post,
            self.siemplify_internal_get,
        ]

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    @router.post(r".*/oauth2(/v2.0)?/token")
    def generate_token(self, _: MockRequest) -> MockResponse:
        """Handle token generation requests."""
        return MockResponse(
            content={"token_type": "Bearer", "access_token": "fake-token"},
            status_code=200,
        )

    # -------------------------------------------------------------------------
    # Machines
    # -------------------------------------------------------------------------

    @router.get(r".*/api/machines/(?P<machine_id>[\w-]+)/vulnerabilities")
    def get_machine_vulnerabilities(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/machines/{id}/vulnerabilities requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/vulnerabilities", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id: str = match.group("machine_id")
        vulnerabilities = self._product.get_machine_vulnerabilities(machine_id)
        return MockResponse(content={"value": vulnerabilities}, status_code=200)

    @router.get(r".*/api/machines/(?P<machine_id>[\w-]+)/recommendations")
    def get_machine_recommendations(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/machines/{machine_id}/recommendations requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/recommendations", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id: str = match.group("machine_id")
        recommendations = self._product.get_recommendations_by_machine_id(machine_id)
        return MockResponse(content={"value": recommendations}, status_code=200)

    @router.get(r".*/api/machines/(?P<machine_id>[\w-]+)/logonusers")
    def get_machine_logon_users(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/machines/{machine_id}/logonusers requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/logonusers", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id: str = match.group("machine_id")
        users = self._product.get_logon_users(machine_id)
        return MockResponse(content={"value": users}, status_code=200)

    @router.get(r".*/api/machines/(?P<machine_id>[\w-]+)/alerts")
    def get_machine_related_alerts(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/machines/{machine_id}/alerts requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/alerts", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id: str = match.group("machine_id")
        alerts = self._product.get_machine_alerts(machine_id)
        return MockResponse(content={"value": alerts}, status_code=200)

    @router.post(r".*/api/machines/(?P<machine_id>[\w-]+)/isolate")
    def isolate_machine(self, request: MockRequest) -> MockResponse:
        """Handle POST /api/machines/{machine_id}/isolate requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/isolate", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id: str = match.group("machine_id")
        task_data = self._product.create_task("Isolate", machine_id)
        return MockResponse(content=task_data, status_code=201)

    @router.post(r".*/api/machines/(?P<machine_id>[\w-]+)/unisolate")
    def unisolate_machine(self, request: MockRequest) -> MockResponse:
        """Handle POST /api/machines/{machine_id}/unisolate requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/unisolate", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id: str = match.group("machine_id")
        task_data = self._product.create_task("Unisolate", machine_id)
        return MockResponse(content=task_data, status_code=201)

    @router.post(r".*/api/machines/(?P<machine_id>[\w-]+)/runAntiVirusScan")
    def run_antivirus_scan(self, request: MockRequest) -> MockResponse:
        """Handle POST /api/machines/{machine_id}/runAntiVirusScan requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/runAntiVirusScan", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id: str = match.group("machine_id")
        task_data = self._product.create_task("RunAntiVirusScan", machine_id)
        return MockResponse(content=task_data, status_code=201)

    @router.post(r".*/api/machines/(?P<machine_id>[\w-]+)/StopAndQuarantineFile")
    def stop_and_quarantine_file(self, request: MockRequest) -> MockResponse:
        """Handle POST /api/machines/{machine_id}/StopAndQuarantineFile requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/StopAndQuarantineFile",
            request.url.path,
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id: str = match.group("machine_id")
        task_data = self._product.create_task("StopAndQuarantineFile", machine_id)
        return MockResponse(content=task_data, status_code=201)

    @router.post(r".*/api/machines/(?P<machine_id>[\w-]+)/runliveresponse")
    def run_live_response(self, request: MockRequest) -> MockResponse:
        """Handle POST /api/machines/{machine_id}/runliveresponse requests."""
        match = re.search(
            r"/api/machines/(?P<machine_id>[\w-]+)/runliveresponse", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        machine_id = match.group("machine_id")
        request_data = request.kwargs.get("json", {})
        commands = request_data.get("Commands", [])
        comment = request_data.get("Comment")

        if not commands or not comment:
            return MockResponse(
                content={"error": {"message": "Invalid request body"}},
                status_code=400,
            )

        command_to_run = json.dumps(commands[0])
        action_id = self._product.add_live_response_action(machine_id, command_to_run)

        machine = self._product.get_machine_by_id(machine_id) or {}
        response_data: SingleJson = {
            "id": action_id,
            "type": "RunLiveResponse",
            "title": None,
            "requestor": "test@contoso.com",
            "requestorComment": comment,
            "status": "Pending",
            "machineId": machine_id,
            "computerDnsName": machine.get("computerDnsName"),
            "creationDateTimeUtc": "2024-01-01T12:00:00.000Z",
            "lastUpdateDateTimeUtc": "2024-01-01T12:00:00.000Z",
            "cancellationRequestor": None,
            "cancellationComment": None,
            "cancellationDateTimeUtc": None,
            "errorHResult": 0,
            "scope": None,
            "commands": [],
        }
        return MockResponse(content=response_data, status_code=201)

    @router.get(r".*/api/machines$")
    def get_machines(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/machines requests."""
        params = request.kwargs.get("params", {})
        filter_str = params.get("$filter") or ""
        machines = []

        if "lastIpAddress eq" in filter_str:
            ip = filter_str.split("'")[1]
            machine = self._product.get_machine_by_ip(ip)
            if machine:
                machines.append(machine)
        elif "startswith(computerDnsName" in filter_str:
            hostname = filter_str.split("'")[1]
            machine = self._product.get_machine_by_hostname(hostname)
            if machine:
                machines.append(machine)
        else:
            machines = self._product.get_all_machines()

        return MockResponse(content={"value": machines}, status_code=200)

    # -------------------------------------------------------------------------
    # Machine actions (tasks)
    # -------------------------------------------------------------------------

    @router.get(r".*/api/machineactions/(?P<action_id>[\w-]+)")
    def get_live_response_status(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/machineactions/{action_id} requests."""
        match = re.search(
            r"/api/machineactions/(?P<action_id>[\w-]+)", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        action_id: str = match.group("action_id")
        action = self._product.get_live_response_action(action_id)
        if not action:
            return MockResponse(
                content={"error": {"message": "Action not found"}}, status_code=404
            )
        action["status"] = "Pending"
        return MockResponse(content=action, status_code=200)

    @router.get(r".*/api/machineactions$")
    def get_machine_actions(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/machineactions (task list) requests."""
        params = request.kwargs.get("params", {}) or {}
        task_id: str | None = params.get("id")
        # Also support OData filter: $filter=id eq <id>
        if not task_id:
            filter_str = params.get("$filter") or ""
            id_match = re.search(r"id eq ([\w-]+)", filter_str)
            if id_match:
                task_id = id_match.group(1)
            else:
                machine_id_match = re.search(r"machineId eq '([\w-]+)'", filter_str)
                if machine_id_match:
                    mid = machine_id_match.group(1)
                    tasks = [
                        t for t in self._product.get_all_tasks()
                        if t.get("machineId") == mid and t.get("status") in ("Pending", "InProgress")
                    ]
                    return MockResponse(content={"value": tasks}, status_code=200)
        if task_id:
            task = self._product.get_task(task_id)
            if task:
                return MockResponse(content={"value": [task]}, status_code=200)
            # Also check live-response actions
            action = self._product.get_live_response_action(task_id)
            if action:
                return MockResponse(content={"value": [action]}, status_code=200)
            return MockResponse(content={"value": []}, status_code=200)
        tasks = self._product.get_all_tasks()
        return MockResponse(content={"value": tasks}, status_code=200)

    # -------------------------------------------------------------------------
    # File endpoints
    # -------------------------------------------------------------------------

    @router.get(r".*/api/files/(?P<file_hash>[\w]+)/alerts")
    def get_file_related_alerts(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/files/{file_hash}/alerts requests."""
        match = re.search(
            r"/api/files/(?P<file_hash>[\w]+)/alerts", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        file_hash: str = match.group("file_hash")
        alerts = self._product.get_file_alerts(file_hash)
        return MockResponse(content={"value": alerts}, status_code=200)

    @router.get(r".*/api/files/(?P<file_hash>[\w]+)/machines")
    def get_file_related_machines(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/files/{file_hash}/machines requests."""
        match = re.search(
            r"/api/files/(?P<file_hash>[\w]+)/machines", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        file_hash: str = match.group("file_hash")
        machines = self._product.get_file_machines(file_hash)
        return MockResponse(content={"value": machines}, status_code=200)

    @router.get(r".*/api/files/(?P<file_hash>[\w]+)/stats")
    def get_file_stats(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/files/{file_hash}/stats requests."""
        match = re.search(
            r"/api/files/(?P<file_hash>[\w]+)/stats", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        file_hash: str = match.group("file_hash")
        stats = self._product.get_file_stats_data(file_hash)
        if not stats:
            return MockResponse(
                content={"error": {"message": "File not found"}}, status_code=404
            )
        return MockResponse(content=stats, status_code=200)

    @router.get(r".*/api/files/(?P<file_hash>[\w]+)$")
    def get_file_info(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/files/{file_hash} requests."""
        match = re.search(r"/api/files/(?P<file_hash>[\w]+)$", request.url.path)
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        file_hash: str = match.group("file_hash")
        info = self._product.get_file_info(file_hash)
        if not info:
            return MockResponse(
                content={"error": {"message": "File not found"}}, status_code=404
            )
        return MockResponse(content=info, status_code=200)

    # -------------------------------------------------------------------------
    # Advanced hunting query
    # -------------------------------------------------------------------------

    @router.post(r".*/api/advancedqueries/run")
    def run_advanced_hunting_query(self, _request: MockRequest) -> MockResponse:
        """Handle POST /api/advancedqueries/run requests."""
        result = self._product.get_hunting_query_result()
        return MockResponse(content=result, status_code=200)

    # -------------------------------------------------------------------------
    # Alerts (generic list endpoint, also used for test_connectivity)
    # -------------------------------------------------------------------------

    @router.get(r".*/api/alerts")
    def get_alerts_or_test_connectivity(self, _request: MockRequest) -> MockResponse:
        """Handle GET /api/alerts requests (list + connectivity test)."""
        alerts = self._product.get_alerts()
        return MockResponse(content={"value": alerts}, status_code=200)

    # -------------------------------------------------------------------------
    # Update alert
    # -------------------------------------------------------------------------

    @router.patch(r".*/api/alerts/(?P<alert_id>[\w-]+)")
    def update_alert(self, request: MockRequest) -> MockResponse:
        """Handle PATCH /api/alerts/{alert_id} requests."""
        match = re.search(r"/api/alerts/(?P<alert_id>[\w-]+)", request.url.path)
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        alert_id: str = match.group("alert_id")
        alert = self._product.get_updateable_alert(alert_id)
        if not alert:
            return MockResponse(
                content={"error": {"message": "Alert not found"}}, status_code=404
            )
        # Merge the patch body into the stored alert
        patch_data: SingleJson = request.kwargs.get("json", {})
        alert.update({k: v for k, v in patch_data.items() if v is not None})
        return MockResponse(content=alert, status_code=200)

    # -------------------------------------------------------------------------
    # Indicators
    # -------------------------------------------------------------------------

    @router.get(r".*/api/indicators")
    def get_indicators(self, _request: MockRequest) -> MockResponse:
        """Handle GET /api/indicators requests."""
        indicators = self._product.get_indicators()
        return MockResponse(content={"value": indicators}, status_code=200)

    @router.post(r".*/api/indicators")
    def submit_indicator(self, request: MockRequest) -> MockResponse:
        """Handle POST /api/indicators requests."""
        payload: SingleJson = request.kwargs.get("json", {})
        self._product.record_submitted_indicator(payload)
        response_data: SingleJson = {
            "id": "test-indicator-id",
            "indicatorValue": payload.get("indicatorValue", ""),
            "indicatorType": payload.get("indicatorType", ""),
            "action": payload.get("action", ""),
        }
        return MockResponse(content=response_data, status_code=200)

    @router.delete(r".*/api/indicators/(?P<indicator_id>[\w-]+)")
    def delete_indicator(self, _request: MockRequest) -> MockResponse:
        """Handle DELETE /api/indicators/{indicator_id} requests."""
        return MockResponse(content={}, status_code=204)

    # -------------------------------------------------------------------------
    # User-related alerts
    # -------------------------------------------------------------------------

    @router.get(r".*/api/users/(?P<user_id>[\w\.-]+)/alerts")
    def get_user_related_alerts(self, request: MockRequest) -> MockResponse:
        """Handle GET /api/users/{user_id}/alerts requests."""
        match: re.Match[str] | None = re.search(
            r"/api/users/(?P<user_id>[\w\.-]+)/alerts", request.url.path
        )
        if not match:
            return MockResponse(
                content={"error": {"message": "URL pattern not matched"}},
                status_code=404,
            )
        user_id: str = match.group("user_id")
        user_alerts_data: SingleJson | None = (
            self._product.get_user_related_alerts(user_id)
        )

        if user_alerts_data:
            if user_alerts_data.get("failed"):
                return MockResponse(
                    content={"error": {"message": "Failed to fetch alerts"}},
                    status_code=500,
                )
            alerts: list[Alert] = user_alerts_data.get("alerts", [])
            return MockResponse(content={"value": alerts}, status_code=200)

        return MockResponse(content={"value": []}, status_code=200)

    # -------------------------------------------------------------------------
    # Siemplify internal API routes (SDK calls that use the session)
    # -------------------------------------------------------------------------

    @router.post(r".*/api/external/v1/sdk/.*")
    def siemplify_internal_post(self, _request: MockRequest) -> MockResponse:
        """Handle Siemplify internal SDK POST calls (e.g. UpdateEntities)."""
        return MockResponse(content={}, status_code=200)

    @router.get(r".*/api/external/v1/sdk/.*")
    def siemplify_internal_get(self, _request: MockRequest) -> MockResponse:
        """Handle Siemplify internal SDK GET calls."""
        return MockResponse(content={}, status_code=200)

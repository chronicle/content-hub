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

import contextlib
import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class SentinelOne:
    users: list[dict] = dataclasses.field(
        default_factory=lambda: [
            {
                "id": "98765",
                "email": "analyst@company.com",
                "fullName": "Mock Analyst",
                "username": "mock.analyst",
            }
        ]
    )

    alerts: list[dict] = dataclasses.field(
        default_factory=lambda: [
            {
                "node": {
                    "id": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
                    "name": "avm.exe detected as Malware",
                    "severity": "CRITICAL",
                    "status": "NEW",
                    "analystVerdict": "UNDEFINED",
                    "detectedAt": "2026-03-21T16:51:06.684Z",
                    "createdAt": "2026-03-21T16:51:06.759Z",
                    "lastSeenAt": "2026-03-21T16:51:18.468Z",
                }
            }
        ]
    )

    details: dict[str, dict] = dataclasses.field(
        default_factory=lambda: {
            "019d114e-e4f4-7ad6-82c3-9829b6d0a801": {
                "id": "019d114e-e4f4-7ad6-82c3-9829b6d0a801",
                "externalId": "2440104020909548527",
                "name": "avm.exe detected as Malware",
                "description": (
                    "Windows memory events analysis detected an attempt to exploit the kernel module ntoskrnl."
                ),
                "severity": "CRITICAL",
                "status": "NEW",
                "analystVerdict": "UNDEFINED",
                "classification": "MALWARE",
                "confidenceLevel": "MALICIOUS",
                "detectedAt": "2026-03-21T16:51:06.684Z",
                "createdAt": "2026-03-21T16:51:06.759Z",
                "firstSeenAt": "2026-03-21T16:51:06.684Z",
                "lastSeenAt": "2026-03-21T16:51:18.468Z",
                "updatedAt": "2026-03-21T16:51:18.468Z",
                "ticketId": None,
                "storylineId": "21932D9A857726BC",
                "selfLink": "https://usea1-dfir.sentinelone.net/incidents/unified-alerts?alertId=019d114e-e4f4-7ad6-82c3-9829b6d0a801",
                "dataSources": [],
                "attackSurfaces": ["ENDPOINT"],
                "labels": [],
                "noteExists": False,
                "result": "UNMITIGATED",
                "preemptiveMitigationType": None,
                "aiInvestigation": None,
                "analytics": {
                    "category": "Reputation",
                    "name": "Agent Policy",
                    "typeValue": "DYNAMIC",
                    "uid": None,
                },
                "assignee": None,
                "assets": [
                    {
                        "id": "zruywtea64rhc5zdd5frofa3hm",
                        "name": "w19sns-10c5fa27",
                        "category": "Server",
                        "subcategory": "Virtual Machine",
                        "assetTypeClassifier": "GCP Compute Instance",
                        "osType": "WINDOWS",
                        "osVersion": "Windows Server 2019 Datacenter 17763",
                        "agentUuid": "817398809a406af377ebb6bb617a2e05a89e5e7e",
                        "agentVersion": "25.2.5.437",
                        "connectivityToConsole": "ONLINE",
                        "decommissioned": False,
                        "deleted": False,
                        "lastLoggedInUser": None,
                        "pendingReboot": False,
                        "policy": None,
                        "primary": True,
                        "role": None,
                        "status": "ACTIVE",
                        "origin": "RESOURCES",
                    }
                ],
                "detectionTime": {
                    "attacker": None,
                    "scope": {
                        "accountId": "1235512064263015539",
                        "accountName": "Mandiant",
                        "groupId": "1235512064405621877",
                        "groupName": "Default Group",
                        "siteId": "1235512064330124404",
                        "siteName": "TEST - Default site",
                    },
                    "targetUser": {"domain": None, "emailAddress": "", "name": None},
                },
                "indicators": [
                    {
                        "uid": "117",
                        "type": "Information gathered for kernel exploitation",
                        "message": " ",
                        "eventTime": "2026-03-21T16:51:06.684Z",
                        "severity": "CRITICAL",
                    }
                ],
                "observables": [
                    {
                        "name": "process.name",
                        "type": "PROCESS",
                        "typeName": None,
                        "value": "avm.exe",
                    }
                ],
                "process": {
                    "cmdLine": "avm.exe",
                    "parentName": "cmd.exe (interactive session)",
                    "username": "W19SNS-10C5FA27\\UC",
                    "userDomain": "W19SNS-10C5FA27",
                    "userDisplayName": "UC",
                    "file": {
                        "name": "avm.exe",
                        "path": (
                            "\\Device\\HarddiskVolume3\\Users\\UC\\Downloads\\"
                            "vt_sample_357780eeb259edad54a9ff13948b8633f8aa042fbe2cbc5aa914c335aef7321e"
                            "\\avm.exe"
                        ),
                        "size": 422912,
                        "md5": None,
                        "sha1": "a60c6a07d3ba6c2d9bf68def208566533398fe8f",
                        "sha256": "4aaf5558277d742b180e3208e4340cc98dd0b94baf5c940c5ef0b0c2d9eea707",
                        "certSubject": None,
                        "certSerialNumber": None,
                        "certExpiresAt": None,
                        "signatureVerification": "Not Signed",
                    },
                },
            }
        }
    )

    def get_unified_alerts(
        self, first: int, view_type: str, after: str | None = None
    ) -> SingleJson:
        """Mock method to return unified alerts matching GraphQL response format with pagination."""
        start = 0
        if after and after.startswith("cursor_"):
            with contextlib.suppress(ValueError):
                start = int(after.split("_")[1]) + 1

        sliced_edges = self.alerts[start : start + first]
        has_next_page = (start + first) < len(self.alerts)
        end_cursor = f"cursor_{start + len(sliced_edges) - 1}" if sliced_edges else None

        return {
            "data": {
                "alerts": {
                    "pageInfo": {
                        "hasNextPage": has_next_page,
                        "endCursor": end_cursor if has_next_page else None,
                    },
                    "edges": sliced_edges,
                }
            }
        }

    def get_alert_details(self, alert_id: str) -> SingleJson:
        """Mock method to return alert details matching GraphQL response format."""
        return {"data": {"alert": self.details.get(alert_id, {})}}

    def trigger_actions(self, actions: list[dict], alert_filter: dict) -> SingleJson:
        """Mock method to trigger actions on alerts and return GraphQL response format."""
        # Extract alert ID from filter
        alert_id = None
        with contextlib.suppress(Exception):
            alert_id = alert_filter["or"][0]["and"][0]["stringEqual"]["value"]

        # If alert ID is not found or not in details, return a mock error
        if not alert_id or alert_id not in self.details:
            return {
                "data": {
                    "alertTriggerActions": {
                        "__typename": "TriggerActionsError",
                        "errors": [
                            {
                                "errorMessage": f"Alert with ID {alert_id} not found.",
                                "errorPayload": None,
                            }
                        ],
                    }
                }
            }

        # Apply updates to the alert in the mock DB
        alert = self.details[alert_id]
        success_details = [{"id": alert_id}]
        action_results = []

        for action in actions:
            action_id = action.get("id")
            payload = action.get("payload") or {}

            if action_id == "S1/alert/statusUpdate" and "status" in payload:
                alert["status"] = payload["status"]["value"]
            elif (
                action_id == "S1/alert/analystVerdictUpdate"
                and "analystVerdict" in payload
            ):
                alert["analystVerdict"] = payload["analystVerdict"]["value"]
            elif action_id == "S1/alert/assignUser" and "assignUser" in payload:
                assignee_val = payload["assignUser"]["value"]
                if assignee_val is None:
                    alert["assignee"] = None
                else:
                    alert["assignee"] = {
                        "userId": str(assignee_val),
                        "fullName": "Mock Analyst",
                        "email": "analyst@example.com",
                    }

            action_results.append(
                {
                    "actionId": action_id,
                    "alertCount": 1,
                    "success": success_details,
                    "failure": [],
                    "skip": [],
                }
            )

        return {
            "data": {
                "alertTriggerActions": {
                    "__typename": "ActionsTriggered",
                    "actions": action_results,
                }
            }
        }

    def get_users(self, email: str | None = None) -> dict:
        """Mock method to return a list of users filtered by email."""
        filtered_users = (
            [u for u in self.users if u["email"].lower() == email.lower()]
            if email
            else self.users
        )
        return {"data": filtered_users}

    def add_alert_note(
        self,
        alert_id: str,
        text: str,
        plain_text: str | None = None,
        note_type: str | None = None,
    ) -> SingleJson:
        """Mock method to add alert note and return GraphQL response."""
        new_note = {
            "id": "mock_note_id_12345",
            "alertId": alert_id,
            "text": text,
            "type": note_type or "PLAIN_TEXT",
            "createdAt": "2026-06-25T12:00:00Z",
            "updatedAt": "2026-06-25T12:00:00Z",
            "author": {
                "id": "98765",
                "email": "analyst@company.com",
                "fullName": "Mock Analyst",
            },
        }
        return {"data": {"addAlertNote": {"data": [new_note]}}}

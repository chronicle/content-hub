# Copyright 2026 RansomLeak
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

"""In-memory stand-in for a RansomLeak tenant."""

from __future__ import annotations

import dataclasses
from typing import Any

VALID_API_KEY = "rl_acme.0000000000000000000000000000000000000000000000000000000000000000"


@dataclasses.dataclass
class RansomLeak:
    """Mock RansomLeak tenant state used by the mock session."""

    users: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    analytics: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    learning_paths: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    assignments: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    exercises: set[str] = dataclasses.field(default_factory=set)
    enrollments: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    risks: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    risk_endpoint_available: bool = True
    health_endpoint_available: bool = True
    api_key: str = VALID_API_KEY

    def add_user(self, user: dict[str, Any], analytics: dict[str, Any] | None = None) -> None:
        self.users.append(user)
        self.analytics[user["id"]] = analytics or {
            "exercisesCompleted": 0,
            "totalLearningTimeMinutes": 0,
            "campaignsCompleted": 0,
            "campaignsInProgress": 0,
            "campaignsOverdue": 0,
            "exerciseHistory": [],
        }

    def find_user(self, email: str) -> dict[str, Any] | None:
        return next((u for u in self.users if u["email"].lower() == email.lower()), None)

    def enroll(
        self,
        learning_path_id: str,
        external_ids: list[str],
        emails: list[str],
        due_days: int | None,
    ) -> dict[str, Any]:
        active = [u for u in self.users if not u.get("isDisabled")]
        by_external = {u["externalId"]: u for u in active if u.get("externalId")}
        by_email = {u["email"].lower(): u for u in active}
        enrolled = {e["userId"] for e in self.enrollments if e["learningPathId"] == learning_path_id}
        results: list[dict[str, Any]] = []
        not_found: list[str] = []
        counts = {"assigned": 0, "alreadyEnrolled": 0}
        requested = [("externalUserId", x, by_external.get(x)) for x in external_ids] + [
            ("email", e.lower(), by_email.get(e.lower())) for e in emails
        ]
        for key, value, user in requested:
            if user is None:
                not_found.append(value)
                results.append({key: value, "status": "not_found"})
                continue
            if user["id"] in enrolled:
                counts["alreadyEnrolled"] += 1
                status = "already_enrolled"
            else:
                enrolled.add(user["id"])
                self.enrollments.append({"learningPathId": learning_path_id, "userId": user["id"], "dueDays": due_days})
                counts["assigned"] += 1
                status = "enrolled"
            results.append({key: value, "userId": user["id"], "status": status, "enrollmentId": f"enr-{user['id']}"})
        return {**counts, "skippedUnlicensed": 0, "notFound": not_found, "results": results}

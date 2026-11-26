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

"""Typed request and response models for the RansomLeak partner API."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .constants import REQUEST_TIMEOUT_SECONDS

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


@dataclasses.dataclass(slots=True, frozen=True)
class RansomLeakConfig:
    """Connection settings for RansomLeakManager.

    Attributes:
        api_root: The tenant URL, e.g. https://acme.ransomleak.com.
        api_key: A RansomLeak API key with the `integration` scope.
        verify_ssl: Whether to verify the server TLS certificate.
        timeout: Per-request timeout in seconds.

    """

    api_root: str
    api_key: str
    verify_ssl: bool = True
    timeout: int = REQUEST_TIMEOUT_SECONDS


@dataclasses.dataclass(slots=True, frozen=True)
class AssignmentRequest:
    """A request to assign one exercise to one existing user.

    Attributes:
        exercise_slug: Slug of the exercise to assign.
        email: The assignee's email address.
        idempotency_key: Stable key; repeating it returns the original assignment.
        reference: Optional originating case ID, stored for audit.

    """

    exercise_slug: str
    email: str
    idempotency_key: str
    reference: str | None = None


@dataclasses.dataclass(slots=True, frozen=True)
class LearningPath:
    """A published learning path users can be enrolled in."""

    id: str
    name: str | None
    description: str | None

    @classmethod
    def from_json(cls, data: SingleJson) -> LearningPath | None:
        """Parse an API record; returns None when it has no ID (it cannot be enrolled in).

        Args:
            data: The raw learning path record.

        Returns:
            The learning path, or None.

        """
        path_id = data.get("id")
        if not path_id:
            return None
        return cls(
            id=str(path_id),
            name=_optional_str(data.get("name")),
            description=_optional_str(data.get("description")),
        )

    def to_json(self) -> SingleJson:
        """Return the JSON result shape (`id`, `name`, `description`)."""
        return {"id": self.id, "name": self.name, "description": self.description}


@dataclasses.dataclass(slots=True, frozen=True)
class Assignment:
    """A created remediation assignment."""

    assignment_id: str | None
    user_id: str | None
    status: str | None
    created_at: str | None

    @classmethod
    def from_json(cls, data: SingleJson) -> Assignment:
        """Parse an API assignment record; missing or null fields become None.

        Args:
            data: The raw assignment record.

        Returns:
            The assignment.

        """
        return cls(
            assignment_id=_optional_str(data.get("assignmentId")),
            user_id=_optional_str(data.get("userId")),
            status=_optional_str(data.get("status")),
            created_at=_optional_str(data.get("createdAt")),
        )


@dataclasses.dataclass(slots=True, frozen=True)
class EnrollmentCounts:
    """Counters from one learning path enrollment call; JSON nulls become 0."""

    assigned: int = 0
    already_enrolled: int = 0
    skipped_unlicensed: int = 0

    @classmethod
    def from_json(cls, data: SingleJson) -> EnrollmentCounts:
        """Parse the counters of an enrollment response.

        Args:
            data: The raw enrollment response.

        Returns:
            The counters, with missing or null values as 0.

        """
        return cls(
            assigned=int(data.get("assigned") or 0),
            already_enrolled=int(data.get("alreadyEnrolled") or 0),
            skipped_unlicensed=int(data.get("skippedUnlicensed") or 0),
        )

    def __add__(self, other: EnrollmentCounts) -> EnrollmentCounts:
        """Sum two sets of counters."""
        return EnrollmentCounts(
            assigned=self.assigned + other.assigned,
            already_enrolled=self.already_enrolled + other.already_enrolled,
            skipped_unlicensed=self.skipped_unlicensed + other.skipped_unlicensed,
        )

    def to_json(self) -> SingleJson:
        """Return the JSON result shape."""
        return dataclasses.asdict(self)

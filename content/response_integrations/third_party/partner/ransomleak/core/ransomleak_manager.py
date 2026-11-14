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

"""HTTP client for the RansomLeak partner integration API."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import requests

from .constants import (
    ASSIGNMENT_SOURCE,
    ENDPOINTS,
    MAX_DUE_DAYS,
    MAX_ENROLLMENT_BATCH,
    MIN_DUE_DAYS,
    REQUEST_TIMEOUT_SECONDS,
)
from .exceptions import (
    RansomLeakAuthError,
    RansomLeakError,
    RansomLeakNotFoundError,
    RansomLeakValidationError,
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_email(value: str | None) -> bool:
    """Return True when the value looks like an email address.

    Args:
        value: The candidate string.

    Returns:
        True for a syntactically plausible email address.

    """
    return bool(value) and bool(EMAIL_PATTERN.match(value.strip()))


class RansomLeakManager:
    """Thin client for the RansomLeak `/api/integration` partner API.

    Authentication is a per-tenant API key sent as `Authorization: Bearer <key>`.
    """

    def __init__(
        self,
        api_root: str,
        api_key: str,
        verify_ssl: bool = True,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        """Create the client.

        Args:
            api_root: The tenant URL, e.g. https://acme.ransomleak.com.
            api_key: A RansomLeak API key with the `integration` scope.
            verify_ssl: Whether to verify the server TLS certificate.
            timeout: Per-request timeout in seconds.

        """
        self.api_root = api_root.rstrip("/") + "/"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "RansomLeak-GoogleSecOps/1.0",
        })

    def _url(self, endpoint: str, **kwargs: str) -> str:
        return urljoin(self.api_root, ENDPOINTS[endpoint].format(**kwargs).lstrip("/"))

    def _request(self, method: str, endpoint: str, path_params: dict[str, str] | None = None, **kwargs: Any) -> Any:
        url = self._url(endpoint, **(path_params or {}))
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.exceptions.Timeout as error:
            msg = f"Request to RansomLeak timed out after {self.timeout} seconds"
            raise RansomLeakError(msg) from error
        except requests.exceptions.RequestException as error:
            msg = f"Unable to reach RansomLeak at {self.api_root}: {error}"
            raise RansomLeakError(msg) from error
        self._validate_response(response)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as error:
            msg = "RansomLeak returned a non-JSON response. Check that API Root is your tenant URL."
            raise RansomLeakError(msg) from error

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:300] or response.reason or "Unknown error"
        if isinstance(body, dict):
            message = body.get("message") or body.get("error") or body
            if isinstance(message, list):
                message = "; ".join(str(m) for m in message)
            return str(message)
        return str(body)

    def _validate_response(self, response: requests.Response) -> None:
        if response.ok:
            return
        message = self._error_message(response)
        status = response.status_code
        if status in (401, 403):
            msg = f"Authentication failed (HTTP {status}): {message}. Check the API Key and API Root."
            raise RansomLeakAuthError(msg)
        if status == 404:
            raise RansomLeakNotFoundError(message)
        if status == 400:
            raise RansomLeakValidationError(message)
        msg = f"RansomLeak API error (HTTP {status}): {message}"
        raise RansomLeakError(msg)

    # ----------------------------------------------------------------- health

    def test_connectivity(self) -> bool:
        """Call an authenticated endpoint so an invalid key fails.

        Returns:
            True when the API key is accepted.

        """
        self._request("GET", "health")
        return True

    # ------------------------------------------------------------------ users

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Look up a user by email (case-insensitive).

        Args:
            email: The user's email address.

        Returns:
            The user record, or None when no user matches.

        Raises:
            RansomLeakValidationError: If the value is not an email address.

        """
        if not is_email(email):
            msg = f"'{email}' is not a valid email address"
            raise RansomLeakValidationError(msg)
        users = self._request("GET", "users", params={"email": email.strip().lower(), "limit": 1}) or []
        return users[0] if users else None

    def get_user_analytics(self, user_id: str) -> dict[str, Any]:
        """Get a user's training analytics.

        Args:
            user_id: RansomLeak user UUID.

        Returns:
            Completions, learning time, campaign participation and recent history.

        """
        return self._request("GET", "user_analytics", {"user_id": user_id})

    def get_user_risk(self, user_id: str) -> dict[str, Any] | None:
        """Get a user's current Human Risk Score.

        Args:
            user_id: RansomLeak user UUID.

        Returns:
            The risk record (`score`, `level`, `confidence`, `subScores`, `computedAt`,
            `riskScoringEnabled`), or None when the endpoint or user is not found
            (older RansomLeak versions do not expose risk scores).

        """
        try:
            return self._request("GET", "user_risk", {"user_id": user_id})
        except RansomLeakNotFoundError:
            return None

    # --------------------------------------------------------- learning paths

    def list_learning_paths(self) -> list[dict[str, Any]]:
        """List published learning paths users can be enrolled in.

        Returns:
            Learning paths with `id`, `name` and `description`.

        """
        return self._request("GET", "learning_paths") or []

    def find_learning_path(self, id_or_name: str) -> dict[str, Any] | None:
        """Resolve a learning path by ID or by exact (case-insensitive) name.

        Args:
            id_or_name: Learning path UUID or name.

        Returns:
            The matching learning path, or None.

        """
        needle = id_or_name.strip()
        paths = self.list_learning_paths()
        for path in paths:
            if path.get("id") == needle:
                return path
        lowered = needle.lower()
        for path in paths:
            if (path.get("name") or "").strip().lower() == lowered:
                return path
        return None

    def enroll_learning_path(
        self,
        learning_path_id: str,
        emails: list[str] | None = None,
        due_days: int | None = None,
        external_user_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Enroll users, matched by email and/or RansomLeak `externalId`, in a learning path.

        Args:
            learning_path_id: Learning path UUID.
            emails: The users' email addresses (case-insensitive).
            due_days: Optional deadline in days from now (1-365).
            external_user_ids: The users' external IDs.

        Returns:
            Counts of assigned, already enrolled and unlicensed users, identifiers not found,
            and per-identifier `results` (`status`: enrolled, already_enrolled,
            skipped_unlicensed or not_found).

        Raises:
            RansomLeakValidationError: On invalid input.

        """
        emails = [e.strip().lower() for e in emails or [] if e and e.strip()]
        external_user_ids = [x for x in external_user_ids or [] if x]
        if not emails and not external_user_ids:
            msg = "At least one user is required"
            raise RansomLeakValidationError(msg)
        if len(emails) > MAX_ENROLLMENT_BATCH or len(external_user_ids) > MAX_ENROLLMENT_BATCH:
            msg = f"At most {MAX_ENROLLMENT_BATCH} users can be enrolled per call"
            raise RansomLeakValidationError(msg)
        body: dict[str, Any] = {}
        if emails:
            body["emails"] = emails
        if external_user_ids:
            body["externalUserIds"] = external_user_ids
        if due_days is not None:
            if not MIN_DUE_DAYS <= due_days <= MAX_DUE_DAYS:
                msg = f"Due In Days must be between {MIN_DUE_DAYS} and {MAX_DUE_DAYS}"
                raise RansomLeakValidationError(msg)
            body["dueDays"] = due_days
        return self._request(
            "POST",
            "learning_path_enrollments",
            {"learning_path_id": learning_path_id},
            json=body,
        )

    # ------------------------------------------------------------ assignments

    def create_assignment(
        self,
        exercise_slug: str,
        email: str,
        idempotency_key: str,
        reference: str | None = None,
    ) -> dict[str, Any]:
        """Assign one exercise to one existing user (matched by email).

        Args:
            exercise_slug: Slug of the exercise to assign.
            email: The assignee's email address.
            idempotency_key: Stable key; repeating it returns the original assignment.
            reference: Optional originating case ID, stored for audit.

        Returns:
            The assignment, including `assignmentId` and a signed `deepLink`.

        """
        body: dict[str, Any] = {
            "exerciseSlug": exercise_slug,
            "user": {"email": email.strip().lower()},
            "idempotencyKey": idempotency_key,
            "source": ASSIGNMENT_SOURCE,
        }
        if reference:
            body["reference"] = reference
        return self._request("POST", "assignments", json=body)

    def get_assignment(self, assignment_id: str) -> dict[str, Any]:
        """Get an assignment's lifecycle status.

        Args:
            assignment_id: Assignment UUID.

        Returns:
            The assignment status record.

        """
        return self._request("GET", "assignment", {"assignment_id": assignment_id})

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

import ipaddress
import threading
from typing import TYPE_CHECKING
from urllib.parse import quote, urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import (
    ASSIGNMENT_SOURCE,
    BLOCKED_API_HOSTS,
    ENDPOINTS,
    MAX_DUE_DAYS,
    MIN_DUE_DAYS,
    RETRY_BACKOFF_FACTOR,
    RETRY_METHODS,
    RETRY_STATUS_CODES,
    RETRY_TOTAL,
    USER_AGENT,
)
from .data_models import Assignment, LearningPath
from .exceptions import (
    RansomLeakAuthError,
    RansomLeakError,
    RansomLeakNotFoundError,
    RansomLeakValidationError,
)
from .utils import is_email

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from TIPCommon.types import JSON, SingleJson

    from .data_models import AssignmentRequest, RansomLeakConfig


def _is_blocked_host(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    if host in BLOCKED_API_HOSTS or host.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    # fd00:ec2::254 is the AWS IPv6 instance metadata endpoint.
    return (
        address.is_loopback
        or address.is_link_local
        or address.is_unspecified
        or address == ipaddress.ip_address("fd00:ec2::254")
    )


def validate_api_root(api_root: str) -> str:
    """Validate the API Root and normalise it to end with a single "/".

    Args:
        api_root: The configured tenant URL.

    Returns:
        The normalised API Root.

    Raises:
        RansomLeakValidationError: If the URL is not https, has embedded credentials, a query or
            fragment, or targets a loopback, link-local or cloud metadata host.

    """
    value = (api_root or "").strip()
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as error:
        msg = f"API Root '{value}' is not a valid URL"
        raise RansomLeakValidationError(msg) from error
    if parsed.scheme.lower() != "https":
        msg = "API Root must use https://"
        raise RansomLeakValidationError(msg)
    if not hostname:
        msg = "API Root must include a host name"
        raise RansomLeakValidationError(msg)
    if parsed.username is not None or parsed.password is not None:
        msg = "API Root must not contain credentials"
        raise RansomLeakValidationError(msg)
    if parsed.query or parsed.fragment:
        msg = "API Root must not contain a query string or fragment"
        raise RansomLeakValidationError(msg)
    if _is_blocked_host(hostname):
        msg = f"API Root host '{hostname}' is not allowed"
        raise RansomLeakValidationError(msg)
    return value.rstrip("/") + "/"


def validate_api_key(api_key: str) -> str:
    """Strip the API key and reject values that cannot be sent as a header.

    Args:
        api_key: The configured API key.

    Returns:
        The stripped API key.

    Raises:
        RansomLeakValidationError: If the key is empty or contains a line break.

    """
    value = (api_key or "").strip()
    if not value:
        msg = "API Key is required"
        raise RansomLeakValidationError(msg)
    if "\r" in value or "\n" in value:
        msg = "API Key must not contain line breaks"
        raise RansomLeakValidationError(msg)
    return value


def _extract_error_message(response: requests.Response) -> str:
    try:
        body: object = response.json()
    except ValueError:
        return response.text[:300] or response.reason or "Unknown error"
    if isinstance(body, dict):
        message = body.get("message") or body.get("error") or body
        if isinstance(message, list):
            message = "; ".join(str(m) for m in message)
        return str(message)
    return str(body)


def _validate_response(response: requests.Response) -> None:
    if response.ok:
        return
    message = _extract_error_message(response)
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


def _as_single_json(data: JSON | None) -> SingleJson:
    return data if isinstance(data, dict) else {}


class RansomLeakManager:
    """Thin client for the RansomLeak `/api/integration` partner API.

    Authentication is a per-tenant API key sent as `Authorization: Bearer <key>`.
    Each thread gets its own requests.Session (it is not thread-safe); every session
    created is tracked so close() releases all connection pools.
    """

    def __init__(self, config: RansomLeakConfig) -> None:
        """Create the client.

        Args:
            config: The connection settings.

        Raises:
            RansomLeakValidationError: If the API Root or API Key is invalid.

        """
        self.api_root: str = validate_api_root(config.api_root)
        self.timeout: int = config.timeout
        self._verify_ssl: bool = config.verify_ssl
        self._headers: dict[str, str] = {
            "Authorization": f"Bearer {validate_api_key(config.api_key)}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        self._local = threading.local()
        self._sessions: list[requests.Session] = []
        self._sessions_lock = threading.Lock()

    def _get_or_create_session(self) -> requests.Session:
        """Return this thread's HTTP session, creating and tracking it on first use."""
        session: requests.Session | None = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.verify = self._verify_ssl
            session.headers.update(self._headers)
            retry = Retry(
                total=RETRY_TOTAL,
                backoff_factor=RETRY_BACKOFF_FACTOR,
                status_forcelist=RETRY_STATUS_CODES,
                allowed_methods=RETRY_METHODS,
                raise_on_status=False,
            )
            session.mount("https://", HTTPAdapter(max_retries=retry))
            self._local.session = session
            with self._sessions_lock:
                self._sessions.append(session)
        return session

    def close(self) -> None:
        """Close every HTTP session this client created, on any thread."""
        with self._sessions_lock:
            sessions, self._sessions = self._sessions, []
        for session in sessions:
            session.close()
        self._local = threading.local()

    def _url(self, endpoint: str, path_params: Mapping[str, str] | None = None) -> str:
        encoded_params = {key: quote(str(value), safe="") for key, value in (path_params or {}).items()}
        return urljoin(self.api_root, ENDPOINTS[endpoint].format(**encoded_params).lstrip("/"))

    def _send(self, send: Callable[[], requests.Response]) -> JSON | None:
        try:
            response = send()
        except requests.exceptions.Timeout as error:
            msg = f"Request to RansomLeak timed out after {self.timeout} seconds"
            raise RansomLeakError(msg) from error
        except requests.exceptions.RequestException as error:
            msg = f"Unable to reach RansomLeak at {self.api_root}: {error}"
            raise RansomLeakError(msg) from error
        _validate_response(response)
        if not response.content:
            return None
        try:
            body: JSON = response.json()
        except ValueError as error:
            msg = "RansomLeak returned a non-JSON response. Check that API Root is your tenant URL."
            raise RansomLeakError(msg) from error
        return body

    def _get(
        self,
        endpoint: str,
        path_params: Mapping[str, str] | None = None,
        params: Mapping[str, str | int] | None = None,
    ) -> JSON | None:
        url = self._url(endpoint, path_params)
        session = self._get_or_create_session()
        return self._send(lambda: session.get(url, params=params, timeout=self.timeout))

    def _post(
        self,
        endpoint: str,
        json_body: SingleJson,
        path_params: Mapping[str, str] | None = None,
    ) -> SingleJson:
        url = self._url(endpoint, path_params)
        session = self._get_or_create_session()
        return _as_single_json(self._send(lambda: session.post(url, json=json_body, timeout=self.timeout)))

    def test_connectivity(self) -> bool:
        """Call an authenticated endpoint so an invalid key fails.

        Falls back to the Grafana health probe on backends that predate
        `/api/integration/health` (404).

        Returns:
            True when the API key is accepted.

        """
        try:
            self._get("health")
        except RansomLeakNotFoundError:
            self._get("legacy_health")
        return True

    def get_user_by_email(self, email: str) -> SingleJson | None:
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
        users = self._get("users", params={"email": email.strip().lower(), "limit": 1})
        if isinstance(users, list) and users and isinstance(users[0], dict):
            return users[0]
        return None

    def get_user_analytics(self, user_id: str) -> SingleJson:
        """Get a user's training analytics.

        Args:
            user_id: RansomLeak user UUID.

        Returns:
            Completions, learning time, campaign participation and recent history
            ({} when the response is empty).

        """
        return _as_single_json(self._get("user_analytics", {"user_id": user_id}))

    def get_user_risk(self, user_id: str) -> SingleJson | None:
        """Get a user's current Human Risk Score.

        Args:
            user_id: RansomLeak user UUID.

        Returns:
            The risk record (`score`, `level`, `confidence`, `subScores`, `computedAt`,
            `riskScoringEnabled`), or None when the endpoint or user is not found
            (older RansomLeak versions do not expose risk scores).

        """
        try:
            risk = self._get("user_risk", {"user_id": user_id})
        except RansomLeakNotFoundError:
            return None
        return risk if isinstance(risk, dict) else None

    def list_learning_paths(self) -> list[LearningPath]:
        """List published learning paths users can be enrolled in.

        Returns:
            Learning paths; records without an ID are dropped.

        """
        records = self._get("learning_paths")
        if not isinstance(records, list):
            return []
        paths = (LearningPath.from_json(record) for record in records if isinstance(record, dict))
        return [path for path in paths if path is not None]

    def find_learning_path(self, id_or_name: str) -> LearningPath | None:
        """Resolve a learning path by ID or by exact (case-insensitive) name.

        Args:
            id_or_name: Learning path UUID or name.

        Returns:
            The matching learning path, or None.

        """
        needle = id_or_name.strip()
        paths = self.list_learning_paths()
        for path in paths:
            if path.id == needle:
                return path
        lowered = needle.lower()
        for path in paths:
            if (path.name or "").strip().lower() == lowered:
                return path
        return None

    def enroll_learning_path(
        self,
        learning_path_id: str,
        emails: list[str],
        due_days: int | None = None,
    ) -> SingleJson:
        """Enroll users, matched by email, in a learning path.

        Args:
            learning_path_id: Learning path UUID.
            emails: The users' email addresses (sent lower-cased), at most MAX_ENROLLMENT_BATCH per call.
            due_days: Optional deadline in days from now (1-365).

        Returns:
            Counts of assigned, already enrolled and unlicensed users, identifiers not found,
            and per-identifier `results` (`status`: enrolled, already_enrolled,
            skipped_unlicensed or not_found); {} when the response is empty.

        Raises:
            RansomLeakValidationError: On invalid input.

        """
        if not emails:
            msg = "At least one user is required"
            raise RansomLeakValidationError(msg)
        body: SingleJson = {"emails": [email.strip().lower() for email in emails]}
        if due_days is not None:
            if not MIN_DUE_DAYS <= due_days <= MAX_DUE_DAYS:
                msg = f"Due In Days must be between {MIN_DUE_DAYS} and {MAX_DUE_DAYS}"
                raise RansomLeakValidationError(msg)
            body["dueDays"] = due_days
        return self._post(
            "learning_path_enrollments",
            body,
            {"learning_path_id": learning_path_id},
        )

    def create_assignment(self, request: AssignmentRequest) -> Assignment:
        """Assign one exercise to one existing user (matched by email).

        Args:
            request: The exercise, assignee, idempotency key and optional reference.

        Returns:
            The created (or, for a repeated idempotency key, the original) assignment.

        """
        body: SingleJson = {
            "exerciseSlug": request.exercise_slug,
            "user": {"email": request.email.strip().lower()},
            "idempotencyKey": request.idempotency_key,
            "source": ASSIGNMENT_SOURCE,
        }
        if request.reference:
            body["reference"] = request.reference
        return Assignment.from_json(self._post("assignments", body))

    def get_assignment(self, assignment_id: str) -> SingleJson:
        """Get an assignment's lifecycle status.

        Args:
            assignment_id: Assignment UUID.

        Returns:
            The assignment status record ({} when the response is empty).

        """
        return _as_single_json(self._get("assignment", {"assignment_id": assignment_id}))

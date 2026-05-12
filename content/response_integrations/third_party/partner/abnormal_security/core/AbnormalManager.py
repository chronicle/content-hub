"""Abnormal Security API Manager for Google SecOps SOAR Integration."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import (
    ACTIVITY_STATUS_ENDPOINT,
    CASE_BY_ID_ENDPOINT,
    CASES_ENDPOINT,
    CONTENT_TYPE_JSON,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    ERROR_MSG_AUTH_FAILED,
    ERROR_MSG_CONNECTION_ERROR,
    ERROR_MSG_INVALID_ACTION,
    ERROR_MSG_INVALID_CASE_ACTION,
    ERROR_MSG_INVALID_REASON,
    ERROR_MSG_INVALID_RESPONSE,
    ERROR_MSG_INVALID_THREAT_ACTION,
    ERROR_MSG_MISSING_ACTIVITY_ID,
    ERROR_MSG_MISSING_CASE_ID,
    ERROR_MSG_MISSING_TENANT_IDS,
    ERROR_MSG_MISSING_THREAT_ID,
    ERROR_MSG_NO_MESSAGES,
    ERROR_MSG_RATE_LIMIT,
    ERROR_MSG_SERVER_ERROR,
    ERROR_MSG_TIMEOUT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    HEADER_USER_AGENT,
    MAX_RETRIES,
    MESSAGES_REMEDIATE_ENDPOINT,
    MESSAGES_SEARCH_ENDPOINT,
    RETRY_BACKOFF_FACTOR,
    RETRY_STATUS_CODES,
    THREAT_BY_ID_ENDPOINT,
    THREATS_ENDPOINT,
    USER_AGENT,
    VALID_CASE_ACTIONS,
    VALID_REMEDIATION_ACTIONS,
    VALID_REMEDIATION_REASONS,
    VALID_THREAT_ACTIONS,
)

logger = logging.getLogger(__name__)


class AbnormalAPIManagerError(Exception):
    """Base exception for Abnormal API Manager errors."""


class AbnormalAuthenticationError(AbnormalAPIManagerError):
    """Raised when authentication fails (HTTP 401)."""


class AbnormalConnectionError(AbnormalAPIManagerError):
    """Raised when connection to API fails."""


class AbnormalRateLimitError(AbnormalAPIManagerError):
    """Raised when API rate limit is exceeded (HTTP 429)."""


class AbnormalValidationError(AbnormalAPIManagerError):
    """Raised when input validation fails."""


class AbnormalManager:
    """Manager for Abnormal Security API operations."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        verify_ssl: bool = DEFAULT_VERIFY_SSL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        if not api_url:
            raise AbnormalValidationError("API URL cannot be empty")
        if not api_key:
            raise AbnormalValidationError("API key cannot be empty")

        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            status_forcelist=RETRY_STATUS_CODES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {
                HEADER_AUTHORIZATION: f"Bearer {self.api_key}",
                HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
                HEADER_USER_AGENT: USER_AGENT,
            }
        )
        session.verify = self.verify_ssl
        return session

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        url = urljoin(self.api_url, endpoint)
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout,
            )

            if response.status_code == 401:
                raise AbnormalAuthenticationError(ERROR_MSG_AUTH_FAILED)
            elif response.status_code == 429:
                raise AbnormalRateLimitError(ERROR_MSG_RATE_LIMIT)
            elif response.status_code >= 500:
                raise AbnormalAPIManagerError(ERROR_MSG_SERVER_ERROR)
            elif response.status_code >= 400:
                raise AbnormalAPIManagerError(f"HTTP {response.status_code}: {response.text}")

            try:
                return response.json()
            except json.JSONDecodeError:
                raise AbnormalAPIManagerError(ERROR_MSG_INVALID_RESPONSE)

        except requests.exceptions.Timeout:
            raise AbnormalConnectionError(ERROR_MSG_TIMEOUT)
        except requests.exceptions.ConnectionError as e:
            raise AbnormalConnectionError(ERROR_MSG_CONNECTION_ERROR) from e
        except (
            AbnormalAPIManagerError,
            AbnormalAuthenticationError,
            AbnormalConnectionError,
            AbnormalRateLimitError,
        ):
            raise
        except requests.exceptions.RequestException as e:
            raise AbnormalAPIManagerError(str(e)) from e

    # ── Connectivity ──────────────────────────────────────────────────────────

    def test_connectivity(self) -> None:
        """Test connectivity and authentication.

        Uses the threats list endpoint with pageSize=1 as a lightweight auth probe.
        A 401 raises AbnormalAuthenticationError; any successful response confirms
        the key is valid regardless of what data is returned.
        """
        self._make_request("GET", THREATS_ENDPOINT, params={"pageSize": 1})

    # ── Search & Respond ──────────────────────────────────────────────────────

    def search_messages(
        self,
        start_time: str,
        end_time: str,
        source: str = "abnormal",
        sender_email: str | None = None,
        subject: str | None = None,
        tenant_ids: list[str] | None = None,
        page_number: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Search for email messages. POST /v1/search"""
        if not start_time or not end_time:
            raise AbnormalValidationError("start_time and end_time are required")

        filters: dict[str, Any] = {"start_time": start_time, "end_time": end_time}
        if sender_email:
            filters["sender_email"] = sender_email
        if subject:
            filters["subject"] = subject
        if tenant_ids:
            filters["tenant_ids"] = [int(t) for t in tenant_ids if t.strip().isdigit()]

        body: dict[str, Any] = {"source": source, "filters": filters}
        params = {"pageNumber": page_number, "pageSize": min(page_size, 1000)}
        return self._make_request("POST", MESSAGES_SEARCH_ENDPOINT, params=params, json_data=body)

    def remediate_messages(
        self,
        action: str,
        source: str,
        messages: list[dict[str, Any]],
        remediation_reason: str,
        tenant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Take remediation action on messages. POST /v1/search/remediate

        Each entry in messages must be a dict with keys:
          tenant_id, raw_message_id, mailbox_name, native_user_id,
          subject, sender, received_time
        """
        if action not in VALID_REMEDIATION_ACTIONS:
            raise AbnormalValidationError(
                f"{ERROR_MSG_INVALID_ACTION} Valid: {', '.join(VALID_REMEDIATION_ACTIONS)}"
            )
        if remediation_reason not in VALID_REMEDIATION_REASONS:
            raise AbnormalValidationError(
                f"{ERROR_MSG_INVALID_REASON} Valid: {', '.join(VALID_REMEDIATION_REASONS)}"
            )
        if not messages:
            raise AbnormalValidationError(ERROR_MSG_NO_MESSAGES)

        body: dict[str, Any] = {
            "action": action,
            "source": source,
            "messages": messages,
            "remediation_reason": remediation_reason,
        }
        if tenant_ids:
            body["tenant_ids"] = [int(t) for t in tenant_ids if t.strip().isdigit()]

        return self._make_request("POST", MESSAGES_REMEDIATE_ENDPOINT, json_data=body)

    def get_activity_status(
        self,
        activity_log_id: str,
        tenant_ids: list[str],
    ) -> dict[str, Any]:
        """Get status of a remediation activity. GET /v1/search/activities/{id}/status"""
        if not activity_log_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_ACTIVITY_ID)
        if not tenant_ids:
            raise AbnormalValidationError(ERROR_MSG_MISSING_TENANT_IDS)

        endpoint = ACTIVITY_STATUS_ENDPOINT.format(activity_log_id=activity_log_id)
        params = {"tenant_ids": ",".join(tenant_ids)}
        return self._make_request("GET", endpoint, params=params)

    # ── Threats ───────────────────────────────────────────────────────────────

    def list_threats(
        self,
        filter_str: str | None = None,
        page_size: int = 100,
        page_number: int = 1,
    ) -> dict[str, Any]:
        """List threats with optional filter. GET /v1/threats"""
        params: dict[str, Any] = {"pageSize": page_size, "pageNumber": page_number}
        if filter_str:
            params["filter"] = filter_str
        return self._make_request("GET", THREATS_ENDPOINT, params=params)

    def get_threat(self, threat_id: str) -> dict[str, Any]:
        """Get a single threat by ID. GET /v1/threats/{id}"""
        if not threat_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_THREAT_ID)
        endpoint = THREAT_BY_ID_ENDPOINT.format(threat_id=threat_id)
        return self._make_request("GET", endpoint)

    def post_threat_action(
        self,
        threat_id: str,
        action: str,
        message_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Take action on a threat.

        Submits a new action by POSTing to /v1/threats/{id} with the action
        verb in the body. The /v1/threats/{id}/actions/{action_id} endpoint
        is GET-only — it returns status for an already-submitted action, not
        a submission endpoint.

        Args:
            threat_id: UUID of the threat to take action on.
            action: Action verb to perform. Must be one of VALID_THREAT_ACTIONS
                (currently "remediate" or "unremediate").
            message_ids: Optional list of message IDs to scope the action to.
                If omitted, the action applies to all messages in the threat.

        Returns:
            Decoded JSON response body from the Abnormal Security API,
            including the submitted action_id and status fields.

        Raises:
            AbnormalValidationError: If threat_id is empty or action is not
                in VALID_THREAT_ACTIONS.
            AbnormalAuthenticationError: If the API rejects the credentials.
            AbnormalRateLimitError: If the API returns HTTP 429.
            AbnormalConnectionError: On network failures or timeouts.
            AbnormalAPIManagerError: On other non-2xx responses or invalid
                response bodies.
        """
        if not threat_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_THREAT_ID)
        if action not in VALID_THREAT_ACTIONS:
            raise AbnormalValidationError(
                f"{ERROR_MSG_INVALID_THREAT_ACTION} Valid: {', '.join(VALID_THREAT_ACTIONS)}"
            )
        endpoint = THREAT_BY_ID_ENDPOINT.format(threat_id=threat_id)
        body: dict[str, Any] = {"action": action}
        if message_ids:
            body["message_ids"] = message_ids
        return self._make_request("POST", endpoint, json_data=body)

    # ── Cases ─────────────────────────────────────────────────────────────────

    def list_cases(
        self,
        filter_str: str | None = None,
        page_size: int = 100,
        page_number: int = 1,
    ) -> dict[str, Any]:
        """List cases with optional filter. GET /v1/cases"""
        params: dict[str, Any] = {"pageSize": page_size, "pageNumber": page_number}
        if filter_str:
            params["filter"] = filter_str
        return self._make_request("GET", CASES_ENDPOINT, params=params)

    def get_case(self, case_id: str) -> dict[str, Any]:
        """Get a single case by ID. GET /v1/cases/{id}"""
        if not case_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_CASE_ID)
        endpoint = CASE_BY_ID_ENDPOINT.format(case_id=case_id)
        return self._make_request("GET", endpoint)

    def post_case_action(self, case_id: str, action: str) -> dict[str, Any]:
        """Take action on a case.

        Submits a new action by POSTing to /v1/cases/{id} with the action
        verb in the body. The /v1/cases/{id}/actions/{action_id} endpoint
        is GET-only — it returns status for an already-submitted action, not
        a submission endpoint.

        Args:
            case_id: ID of the case to take action on.
            action: Action verb to perform. Must be one of VALID_CASE_ACTIONS
                (action_required, acknowledge_resolved, acknowledge_in_progress,
                acknowledge_not_an_attack).

        Returns:
            Decoded JSON response body from the Abnormal Security API,
            including the submitted action_id and status fields.

        Raises:
            AbnormalValidationError: If case_id is empty or action is not
                in VALID_CASE_ACTIONS.
            AbnormalAuthenticationError: If the API rejects the credentials.
            AbnormalRateLimitError: If the API returns HTTP 429.
            AbnormalConnectionError: On network failures or timeouts.
            AbnormalAPIManagerError: On other non-2xx responses or invalid
                response bodies.
        """
        if not case_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_CASE_ID)
        if action not in VALID_CASE_ACTIONS:
            raise AbnormalValidationError(
                f"{ERROR_MSG_INVALID_CASE_ACTION} Valid: {', '.join(VALID_CASE_ACTIONS)}"
            )
        endpoint = CASE_BY_ID_ENDPOINT.format(case_id=case_id)
        body: dict[str, Any] = {"action": action}
        return self._make_request("POST", endpoint, json_data=body)

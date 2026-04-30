"""
Abnormal Security API Manager for Google SecOps SOAR Integration.

Handles all HTTP communication with the Abnormal Security REST API,
including authentication, retry logic, and error handling.
"""

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
    CONTENT_TYPE_JSON,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    ERROR_MSG_AUTH_FAILED,
    ERROR_MSG_CONNECTION_ERROR,
    ERROR_MSG_INVALID_ACTION,
    ERROR_MSG_INVALID_REASON,
    ERROR_MSG_INVALID_RESPONSE,
    ERROR_MSG_MISSING_ACTIVITY_ID,
    ERROR_MSG_MISSING_TENANT_IDS,
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
    SUCCESS_MSG_CONNECTIVITY,
    THREATS_ENDPOINT,
    USER_AGENT,
    VALID_REMEDIATION_ACTIONS,
    VALID_REMEDIATION_REASONS,
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
    """
    Manager class for Abnormal Security API operations.

    Handles HTTP communication with automatic retries, error handling,
    and Bearer token authentication.
    """

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
        except (AbnormalAPIManagerError, AbnormalAuthenticationError, AbnormalConnectionError,
                AbnormalRateLimitError):
            raise
        except requests.exceptions.RequestException as e:
            raise AbnormalAPIManagerError(str(e)) from e

    def test_connectivity(self) -> dict[str, Any]:
        """
        Test connectivity and authentication to the Abnormal Security API.

        Returns:
            dict: Status confirmation with message and raw API response.

        Raises:
            AbnormalAuthenticationError: If the API key is invalid.
            AbnormalConnectionError: If the API is unreachable.
        """
        response = self._make_request("GET", THREATS_ENDPOINT, params={"page_size": 1})
        return {"status": "success", "message": SUCCESS_MSG_CONNECTIVITY, "data": response}

    def search_messages(
        self,
        start_time: str,
        end_time: str,
        sender_email: str | None = None,
        subject: str | None = None,
        tenant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Search for email messages matching the given filter criteria.

        Args:
            start_time: ISO 8601 start time for the search window (required).
            end_time: ISO 8601 end time for the search window (required).
            sender_email: Filter by sender email address (optional).
            subject: Filter by email subject (optional).
            tenant_ids: Tenant IDs to scope the search (optional).

        Returns:
            dict: API response with a ``messages`` list and metadata.

        Raises:
            AbnormalValidationError: If start_time or end_time is missing.
        """
        if not start_time or not end_time:
            raise AbnormalValidationError("start_time and end_time are required")

        params: dict[str, Any] = {"start_time": start_time, "end_time": end_time}
        if sender_email:
            params["sender_email"] = sender_email
        if subject:
            params["subject"] = subject
        if tenant_ids:
            params["tenant_ids"] = ",".join(tenant_ids)

        return self._make_request("GET", MESSAGES_SEARCH_ENDPOINT, params=params)

    def remediate_messages(
        self,
        action: str,
        messages: list[str],
        remediation_reason: str,
        tenant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Take remediation action on email messages.

        Args:
            action: Remediation type — one of ``delete``, ``move_to_inbox``,
                ``submit_to_d360``, ``reclassify``.
            messages: List of message IDs to remediate.
            remediation_reason: One of ``false_negative``, ``false_positive``,
                ``manual_remediation``.
            tenant_ids: Tenant IDs to scope the operation (optional).

        Returns:
            dict: API response containing ``activity_log_id`` for status polling.

        Raises:
            AbnormalValidationError: If action, reason, or messages are invalid.
        """
        if action not in VALID_REMEDIATION_ACTIONS:
            raise AbnormalValidationError(
                f"{ERROR_MSG_INVALID_ACTION} Valid actions: {', '.join(VALID_REMEDIATION_ACTIONS)}"
            )
        if remediation_reason not in VALID_REMEDIATION_REASONS:
            raise AbnormalValidationError(
                f"{ERROR_MSG_INVALID_REASON} Valid reasons: {', '.join(VALID_REMEDIATION_REASONS)}"
            )
        if not messages:
            raise AbnormalValidationError(ERROR_MSG_NO_MESSAGES)

        body: dict[str, Any] = {
            "action": action,
            "messages": messages,
            "remediation_reason": remediation_reason,
        }
        if tenant_ids:
            body["tenant_ids"] = tenant_ids

        return self._make_request("POST", MESSAGES_REMEDIATE_ENDPOINT, json_data=body)

    def get_activity_status(
        self,
        activity_log_id: str,
        tenant_ids: list[str],
    ) -> dict[str, Any]:
        """
        Get the status of a remediation activity.

        Args:
            activity_log_id: Activity log ID returned by remediate_messages (required).
            tenant_ids: Tenant IDs to query for status (required).

        Returns:
            dict: API response with ``status`` and per-message details.

        Raises:
            AbnormalValidationError: If activity_log_id or tenant_ids is empty.
        """
        if not activity_log_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_ACTIVITY_ID)
        if not tenant_ids:
            raise AbnormalValidationError(ERROR_MSG_MISSING_TENANT_IDS)

        endpoint = ACTIVITY_STATUS_ENDPOINT.format(activity_log_id=activity_log_id)
        params = {"tenant_ids": ",".join(tenant_ids)}
        return self._make_request("GET", endpoint, params=params)

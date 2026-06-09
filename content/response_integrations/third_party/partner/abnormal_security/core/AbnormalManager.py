"""Abnormal Security API Manager for Google SecOps SOAR Integration."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import (
    ACTIVITIES_LIST_ENDPOINT,
    ACTIVITY_STATUS_ENDPOINT,
    CASE_ANALYSIS_ENDPOINT,
    CASE_BY_ID_ENDPOINT,
    CASES_ENDPOINT,
    CONTENT_TYPE_JSON,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    ERROR_MSG_AUTH_FAILED,
    ERROR_MSG_CONNECTION_ERROR,
    ERROR_MSG_INVALID_ACTION,
    ERROR_MSG_INVALID_CASE_ACTION,
    ERROR_MSG_INVALID_INQUIRY_REPORT_TYPE,
    ERROR_MSG_INVALID_REASON,
    ERROR_MSG_INVALID_RESPONSE,
    ERROR_MSG_INVALID_THREAT_ACTION,
    ERROR_MSG_MISSING_ACTIVITY_ID,
    ERROR_MSG_MISSING_CASE_ID,
    ERROR_MSG_MISSING_INQUIRY_REPORTER,
    ERROR_MSG_MISSING_THREAT_ID,
    ERROR_MSG_NO_MESSAGES,
    ERROR_MSG_RATE_LIMIT,
    ERROR_MSG_SERVER_ERROR,
    ERROR_MSG_TIMEOUT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    HEADER_USER_AGENT,
    INQUIRY_ENDPOINT,
    MAX_RETRIES,
    MESSAGES_REMEDIATE_ENDPOINT,
    MESSAGES_SEARCH_ENDPOINT,
    RETRY_BACKOFF_FACTOR,
    RETRY_STATUS_CODES,
    THREAT_ATTACHMENTS_ENDPOINT,
    THREAT_BY_ID_ENDPOINT,
    THREAT_LINKS_ENDPOINT,
    THREATS_ENDPOINT,
    USER_AGENT,
    VALID_CASE_ACTIONS,
    VALID_INQUIRY_REPORT_TYPES,
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


_SCIENTIFIC_NOTATION_RE = re.compile(r"-?\d+\.\d+e[+-]?\d+", re.IGNORECASE)


_REQUIRED_REMEDIATE_FIELDS = (
    "tenant_id",
    "raw_message_id",
    "mailbox_name",
    "native_user_id",
    "subject",
    "sender",
    "received_time",
)

_BARE_ID_GUIDANCE = (
    "Search & Respond remediation needs full message objects, not a single message ID. "
    "The /v1/search/remediate API requires these fields per message: "
    f"{', '.join(_REQUIRED_REMEDIATE_FIELDS)} — which a threat event does not carry. "
    "Run the Search Messages action first and pass its JSON output here, or to remediate "
    "the message behind a single threat use the Remediate Threat action instead."
)


def parse_messages_input(messages_json: str) -> list[dict[str, Any]]:
    """Parse the "Messages JSON" action parameter into a list of message objects.

    The Search & Respond remediate endpoint (/v1/search/remediate) requires full
    message objects — see ``_REQUIRED_REMEDIATE_FIELDS``. Those objects come from a
    prior Search Messages step; a bare message ID cannot satisfy the API and a threat
    event does not carry ``tenant_id`` / ``raw_message_id``, so single-message
    remediation must go through the Remediate Threat action instead.

    Accepts:

    1. A JSON array of message objects (the output of Search Messages) — returned
       as-is.
    2. A single JSON object — wrapped into a one-element list.

    Args:
        messages_json: The raw value of the "Messages JSON" action parameter.

    Returns:
        A list of message-object dicts suitable for ``remediate_messages``.

    Raises:
        AbnormalValidationError: If the input is empty, is a scalar/bare message ID
            (which cannot satisfy the remediate schema), or is a numeric ID in
            scientific notation (precision already lost).
    """
    raw = (messages_json or "").strip()
    if not raw:
        raise AbnormalValidationError(f"Messages JSON is required. {_BARE_ID_GUIDANCE}")

    # Scientific notation means a 64-bit message ID was passed as a number and has
    # already lost precision (e.g. -1.08e+18).
    if _SCIENTIFIC_NOTATION_RE.fullmatch(raw):
        raise AbnormalValidationError(f"Message ID lost precision (rendered as a float). {_BARE_ID_GUIDANCE}")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        # Not JSON — a bare message ID can never satisfy the remediate schema.
        raise AbnormalValidationError(_BARE_ID_GUIDANCE) from e

    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    # A bare JSON scalar (int/str) — also insufficient for the remediate schema.
    raise AbnormalValidationError(_BARE_ID_GUIDANCE)


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
        session.headers.update({
            HEADER_AUTHORIZATION: f"Bearer {self.api_key}",
            HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
            HEADER_USER_AGENT: USER_AGENT,
        })
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
            raise AbnormalValidationError(f"{ERROR_MSG_INVALID_ACTION} Valid: {', '.join(VALID_REMEDIATION_ACTIONS)}")
        if remediation_reason not in VALID_REMEDIATION_REASONS:
            raise AbnormalValidationError(f"{ERROR_MSG_INVALID_REASON} Valid: {', '.join(VALID_REMEDIATION_REASONS)}")
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
        tenant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get status of a remediation activity. GET /v1/search/activities/{id}/status

        The status endpoint scopes to the tenants authorized by the API key (resolved
        server-side from the bearer token) and rejects a tenant query param, so
        ``tenant_ids`` is accepted for signature compatibility but not sent.
        """
        if not activity_log_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_ACTIVITY_ID)

        endpoint = ACTIVITY_STATUS_ENDPOINT.format(activity_log_id=activity_log_id)
        return self._make_request("GET", endpoint)

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
            raise AbnormalValidationError(f"{ERROR_MSG_INVALID_THREAT_ACTION} Valid: {', '.join(VALID_THREAT_ACTIONS)}")
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
            raise AbnormalValidationError(f"{ERROR_MSG_INVALID_CASE_ACTION} Valid: {', '.join(VALID_CASE_ACTIONS)}")
        endpoint = CASE_BY_ID_ENDPOINT.format(case_id=case_id)
        body: dict[str, Any] = {"action": action}
        return self._make_request("POST", endpoint, json_data=body)

    # ── Threat sub-resources ──────────────────────────────────────────────────

    def get_threat_attachments(self, threat_id: str) -> dict[str, Any]:
        """List attachments associated with a threat.

        Args:
            threat_id: UUID of the threat.

        Returns:
            Decoded JSON response with the threat's attachments.

        Raises:
            AbnormalValidationError: If threat_id is empty.
            AbnormalAuthenticationError: If the API rejects the credentials.
            AbnormalRateLimitError: If the API returns HTTP 429.
            AbnormalConnectionError: On network failures or timeouts.
            AbnormalAPIManagerError: On other non-2xx responses.
        """
        if not threat_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_THREAT_ID)
        endpoint = THREAT_ATTACHMENTS_ENDPOINT.format(threat_id=threat_id)
        return self._make_request("GET", endpoint)

    def get_threat_links(self, threat_id: str) -> dict[str, Any]:
        """List URLs/links observed in a threat's messages.

        Args:
            threat_id: UUID of the threat.

        Returns:
            Decoded JSON response with the threat's links.

        Raises:
            AbnormalValidationError: If threat_id is empty.
            AbnormalAuthenticationError: If the API rejects the credentials.
            AbnormalRateLimitError: If the API returns HTTP 429.
            AbnormalConnectionError: On network failures or timeouts.
            AbnormalAPIManagerError: On other non-2xx responses.
        """
        if not threat_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_THREAT_ID)
        endpoint = THREAT_LINKS_ENDPOINT.format(threat_id=threat_id)
        return self._make_request("GET", endpoint)

    # ── Case sub-resources ────────────────────────────────────────────────────

    def get_case_analysis(self, case_id: str) -> dict[str, Any]:
        """Get analysis details for a case.

        Args:
            case_id: ID of the case.

        Returns:
            Decoded JSON response with case analysis details.

        Raises:
            AbnormalValidationError: If case_id is empty.
            AbnormalAuthenticationError: If the API rejects the credentials.
            AbnormalRateLimitError: If the API returns HTTP 429.
            AbnormalConnectionError: On network failures or timeouts.
            AbnormalAPIManagerError: On other non-2xx responses.
        """
        if not case_id:
            raise AbnormalValidationError(ERROR_MSG_MISSING_CASE_ID)
        endpoint = CASE_ANALYSIS_ENDPOINT.format(case_id=case_id)
        return self._make_request("GET", endpoint)

    # ── Activities list ───────────────────────────────────────────────────────

    def list_activities(
        self,
        tenant_ids: list[str] | None = None,
        page_size: int = 100,
        page_number: int = 1,
    ) -> dict[str, Any]:
        """List all remediation activities.

        Args:
            tenant_ids: Optional tenant IDs to scope the query to.
            page_size: Results per page (server-capped).
            page_number: Page index, 1-based.

        Returns:
            Decoded JSON response with the activities list.

        Raises:
            AbnormalAuthenticationError: If the API rejects the credentials.
            AbnormalRateLimitError: If the API returns HTTP 429.
            AbnormalConnectionError: On network failures or timeouts.
            AbnormalAPIManagerError: On other non-2xx responses.
        """
        params: dict[str, Any] = {"pageSize": page_size, "pageNumber": page_number}
        if tenant_ids:
            # The /v1/search/activities view reads request.GET.getlist("tenant_ids")
            # (snake_case), so send that key — not camelCase.
            params["tenant_ids"] = ",".join(tenant_ids)
        return self._make_request("GET", ACTIVITIES_LIST_ENDPOINT, params=params)

    # ── Inquiry ───────────────────────────────────────────────────────────────

    def submit_inquiry(
        self,
        report_type: str,
        reporter: str,
        subject: str | None = None,
        sender_email: str | None = None,
        sender_display_name: str | None = None,
        recipient_email: str | None = None,
        recipient_display_name: str | None = None,
        received_time: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Submit an analyst inquiry to Abnormal — typically a false-positive
        or false-negative report on a message the platform did or did not flag.

        Args:
            report_type: One of VALID_INQUIRY_REPORT_TYPES
                ("false-positive" or "false-negative").
            reporter: Identifier of the analyst submitting the report (email
                or username).
            subject: Optional message subject.
            sender_email: Optional sender email address.
            sender_display_name: Optional sender display name.
            recipient_email: Optional recipient email address.
            recipient_display_name: Optional recipient display name.
            received_time: Optional ISO 8601 timestamp the message was received.
            description: Optional free-text analyst note.

        Returns:
            Decoded JSON response acknowledging the submission.

        Raises:
            AbnormalValidationError: If report_type is invalid or reporter
                is empty.
            AbnormalAuthenticationError: If the API rejects the credentials.
            AbnormalRateLimitError: If the API returns HTTP 429.
            AbnormalConnectionError: On network failures or timeouts.
            AbnormalAPIManagerError: On other non-2xx responses.
        """
        if report_type not in VALID_INQUIRY_REPORT_TYPES:
            raise AbnormalValidationError(
                f"{ERROR_MSG_INVALID_INQUIRY_REPORT_TYPE} Valid: {', '.join(VALID_INQUIRY_REPORT_TYPES)}"
            )
        if not reporter:
            raise AbnormalValidationError(ERROR_MSG_MISSING_INQUIRY_REPORTER)

        body: dict[str, Any] = {"report_type": report_type, "reporter": reporter}
        if subject:
            body["subject"] = subject
        if sender_email or sender_display_name:
            sender: dict[str, str] = {}
            if sender_email:
                sender["email_address"] = sender_email
            if sender_display_name:
                sender["display_name"] = sender_display_name
            body["sender"] = sender
        if recipient_email or recipient_display_name:
            recipient: dict[str, str] = {}
            if recipient_email:
                recipient["email_address"] = recipient_email
            if recipient_display_name:
                recipient["display_name"] = recipient_display_name
            body["recipient"] = recipient
        if received_time:
            body["received_time"] = received_time
        if description:
            body["description"] = description

        return self._make_request("POST", INQUIRY_ENDPOINT, json_data=body)

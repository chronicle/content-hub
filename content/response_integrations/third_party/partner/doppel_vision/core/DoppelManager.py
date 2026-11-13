from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR, SingleJson

from .config import IntegrationConfig, create_auth_provider, validate_config
from .constants import API_HOST
from .http_client import HttpClient


class DoppelManager:
    """Client for Doppel Vision v1 and v2 alert APIs."""

    def __init__(
        self,
        config: IntegrationConfig,
        siemplify: ChronicleSOAR | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] | None = None,
        persist_token: bool = True,
    ) -> None:
        """Initialize a manager from a validated integration configuration.

        Args:
            config: Loaded integration configuration.
            siemplify: Optional SOAR SDK object used for token persistence.
            session: Optional shared requests session.
            sleep: Optional sleep callable used by HTTP retries.
            persist_token: Whether to persist OAuth tokens in SOAR context.
        """
        config = validate_config(config)
        self.api_version = config.api_version
        self.api_key = config.api_key
        self.user_api_key = config.user_api_key
        self.org_code = config.org_code
        self.client_id = config.client_id
        self.client_secret = config.client_secret
        self.base_url = f"{API_HOST}/{config.api_version}"
        session = session or requests.Session()
        self.auth_provider = create_auth_provider(
            config,
            siemplify=siemplify,
            session=session,
            persist_token=persist_token,
        )
        self.http_client = HttpClient(auth_provider=self.auth_provider, session=session, sleep=sleep)

    @classmethod
    def from_config(
        cls,
        config: IntegrationConfig,
        siemplify: ChronicleSOAR | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] | None = None,
        persist_token: bool = True,
    ) -> DoppelManager:
        """Create a manager from a validated integration configuration.

        Args:
            config: Loaded integration configuration.
            siemplify: Optional SOAR SDK object used for token persistence.
            session: Optional shared requests session.
            sleep: Optional sleep callable used by HTTP retries.
            persist_token: Whether to persist OAuth tokens in SOAR context.

        Returns:
            Configured DoppelManager instance.
        """
        return cls(config, siemplify=siemplify, session=session, sleep=sleep, persist_token=persist_token)

    def connection_test(self) -> bool:
        """Validate credentials by fetching a single alert.

        Returns:
            True if the connection succeeds.
        """
        self.http_client.request("GET", f"{self.base_url}/alerts", params={"page": 0, "page_size": 1})
        return True

    def get_alert(self, entity: str | None = None, alert_id: str | None = None) -> SingleJson:
        """Fetch a single alert by ID or entity.

        Args:
            entity: Entity value.
            alert_id: Alert ID.

        Returns:
            Raw alert payload dictionary.

        Raises:
            ValueError: If neither or both identifiers are provided, or the response is empty.
        """
        if entity and alert_id:
            raise ValueError("Only one of 'entity' or 'alert_id' can be provided, not both.")
        if not entity and not alert_id:
            raise ValueError("Either 'entity' or 'alert_id' must be provided.")

        params = {"entity": entity} if entity else {"id": alert_id}
        payload = self.http_client.request("GET", f"{self.base_url}/alert", params=params)
        if not payload:
            raise ValueError("Empty response or alert not found.")
        return payload

    def get_alerts(self, filters: SingleJson | None = None) -> list[SingleJson]:
        """Fetch a page of alerts matching the query parameters.

        Args:
            filters: Query filter parameters.

        Returns:
            List of raw alert dictionaries.
        """
        payload = self.http_client.request("GET", f"{self.base_url}/alerts", params=filters or None)
        alerts = payload.get("alerts", []) if isinstance(payload, dict) else []
        return alerts if isinstance(alerts, list) else []

    def create_alert(self, entity: str) -> SingleJson:
        """Create a new alert for a given entity.

        Args:
            entity: Entity value to alert on.

        Returns:
            Raw created-alert payload dictionary.

        Raises:
            ValueError: If the response is empty.
        """
        payload = self.http_client.request("POST", f"{self.base_url}/alert", json_body={"entity": entity})
        if not payload:
            raise ValueError("Empty response or alert creation failed.")
        return payload

    def update_alert(
        self,
        queue_state: str | None = None,
        entity_state: str | None = None,
        entity: str | None = None,
        alert_id: str | None = None,
        comment: str | None = None,
    ) -> SingleJson:
        """Update an existing alert using either the entity or the alert ID.

        Args:
            queue_state: Optional queue state to apply.
            entity_state: Optional entity state to apply.
            entity: Entity value that identifies the alert.
            alert_id: Alert ID that identifies the alert.
            comment: Optional comment to send as the API `comment` field.

        Returns:
            Raw updated-alert payload dictionary.

        Raises:
            ValueError: If identifiers or update fields are invalid, or the response is empty.
        """
        if entity and alert_id:
            raise ValueError("Only one of 'entity' or 'alert_id' can be provided, not both.")
        if not entity and not alert_id:
            raise ValueError("Either 'entity' or 'alert_id' must be provided.")

        body: SingleJson = {}
        if queue_state:
            body["queue_state"] = queue_state
        if entity_state:
            body["entity_state"] = entity_state
        if comment:
            body["comment"] = comment
        if not body:
            raise ValueError("At least one of Queue_State, Entity_State, or Comment must be provided.")

        params = {"entity": entity} if entity else {"id": alert_id}
        payload = self.http_client.request("PUT", f"{self.base_url}/alert", params=params, json_body=body)
        if not payload:
            raise ValueError("Empty response or update failed.")
        return payload

from __future__ import annotations

from typing import Any

import requests

from .alert_models import normalize_alert, normalize_alert_list
from .config import IntegrationConfig, create_auth_provider, resolve_api_version, validate_config
from .constants import API_HOST, API_VERSION_V1
from .http_client import HttpClient


class DoppelManager:
    def __init__(
        self,
        api_key: str | None = None,
        user_api_key: str | None = None,
        org_code: str | None = None,
        api_version: str = API_VERSION_V1,
        client_id: str | None = None,
        client_secret: str | None = None,
        siemplify: Any | None = None,
        session: requests.Session | None = None,
        sleep: Any | None = None,
    ) -> None:
        config = validate_config(
            IntegrationConfig(
                api_version=resolve_api_version(api_version),
                api_key=api_key,
                user_api_key=user_api_key,
                org_code=org_code,
                client_id=client_id,
                client_secret=client_secret,
            ),
        )
        self._init_from_config(config, siemplify=siemplify, session=session, sleep=sleep)

    @classmethod
    def from_config(
        cls,
        config: IntegrationConfig,
        siemplify: Any | None = None,
        session: requests.Session | None = None,
        sleep: Any | None = None,
        persist_token: bool = True,
    ) -> DoppelManager:
        manager = cls.__new__(cls)
        manager._init_from_config(
            config,
            siemplify=siemplify,
            session=session,
            sleep=sleep,
            persist_token=persist_token,
        )
        return manager

    def _init_from_config(
        self,
        config: IntegrationConfig,
        siemplify: Any | None = None,
        session: requests.Session | None = None,
        sleep: Any | None = None,
        persist_token: bool = True,
    ) -> None:
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
        self.http_client = HttpClient(
            auth_provider=self.auth_provider,
            session=session,
            sleep=sleep,
        )

    def connection_test(self) -> bool:
        """Tests connectivity and credentials against GET /alerts."""
        self.http_client.request(
            "GET",
            f"{self.base_url}/alerts",
            params={"page": 0, "page_size": 1},
        )
        return True

    def get_alert(self, entity: str | None = None, alert_id: str | None = None) -> dict[str, Any]:
        """Fetches an alert using either the entity or the alert ID, but not both."""
        if entity and alert_id:
            raise ValueError("Only one of 'entity' or 'alert_id' can be provided, not both.")
        if not entity and not alert_id:
            raise ValueError("Either 'entity' or 'alert_id' must be provided.")

        params = {"entity": entity} if entity else {"id": alert_id}
        payload = self.http_client.request("GET", f"{self.base_url}/alert", params=params)
        if not payload:
            raise ValueError("Empty response or alert not found.")
        return payload

    def get_alerts(self, filters: dict[str, Any] | None = None) -> list[Any]:
        """Fetches alerts from Doppel, optionally filtered by criteria."""
        payload = self.http_client.request(
            "GET",
            f"{self.base_url}/alerts",
            params=filters or None,
        )
        alerts = payload.get("alerts", []) if isinstance(payload, dict) else []
        return alerts

    def create_alert(self, entity: str) -> dict[str, Any]:
        """Creates a new alert for a given entity in Doppel."""
        payload = self.http_client.request(
            "POST",
            f"{self.base_url}/alert",
            json_body={"entity": entity},
        )
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
    ) -> dict[str, Any]:
        """Updates an existing alert using either the entity or the alert ID."""
        if entity and alert_id:
            raise ValueError("Only one of 'entity' or 'alert_id' can be provided, not both.")
        if not entity and not alert_id:
            raise ValueError("Either 'entity' or 'alert_id' must be provided.")

        body: dict[str, Any] = {}
        if queue_state:
            body["queue_state"] = queue_state
        if entity_state:
            body["entity_state"] = entity_state
        if comment:
            body["comment"] = comment
        if not body:
            raise ValueError("At least one of Queue_State, Entity_State, or Comment must be provided.")

        params = {"entity": entity} if entity else {"id": alert_id}
        payload = self.http_client.request(
            "PUT",
            f"{self.base_url}/alert",
            params=params,
            json_body=body,
        )
        if not payload:
            raise ValueError("Empty response or update failed.")
        return payload

    def normalize_alert(self, raw_alert: Any) -> dict[str, Any] | None:
        return normalize_alert(raw_alert)

    def normalize_alerts(self, raw_alerts: Any) -> list[dict[str, Any]]:
        return normalize_alert_list(raw_alerts)

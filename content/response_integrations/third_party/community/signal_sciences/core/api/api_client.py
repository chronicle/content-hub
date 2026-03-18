from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from TIPCommon.base.interfaces import Apiable

from ..constants import ENDPOINTS
from .api_utils import validate_response

if TYPE_CHECKING:
    from TIPCommon.base.interfaces.logger import ScriptLogger

    from ..auth import AuthenticatedSession


class ApiParameters(NamedTuple):
    api_root: str
    corp_name: str


class SignalSciencesApiClient(Apiable):
    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(authenticated_session=authenticated_session, configuration=configuration)
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root
        self.corp_name: str = configuration.corp_name

    def _get_url(self, path: str) -> str:
        """Construct the full URL for a given path."""
        base = f"{self.api_root.rstrip('/')}/api/v0/corps/{self.corp_name}"
        path = path.lstrip('/')
        return f"{base}/{path}" if path else base

    def test_connectivity(self) -> None:
        """Test API connectivity by fetching the corp details."""
        url = self._get_url("")
        response = self.session.get(url)
        validate_response(response, "Failed to connect to Signal Sciences")

    def list_sites(self, limit: int = 100, page: int = 1) -> list[dict[str, Any]]:
        """List sites in the corporation."""
        path = ENDPOINTS["list-sites"]
        url = self._get_url(path)
        params = {"limit": limit, "page": page}
        response = self.session.get(url, params=params)
        validate_response(response, "Failed to list sites")
        return response.json().get("data", [])

    def get_allowlist(self, site_name: str) -> list[dict[str, Any]]:
        """Get allowlist for a site."""
        path = ENDPOINTS["get-allowlist"].format(site_name=site_name)
        url = self._get_url(path)
        response = self.session.get(url)
        validate_response(response, f"Failed to get allowlist for site {site_name}")
        return response.json().get("data", [])

    def get_blocklist(self, site_name: str) -> list[dict[str, Any]]:
        """Get blocklist for a site."""
        path = ENDPOINTS["get-blocklist"].format(site_name=site_name)
        url = self._get_url(path)
        response = self.session.get(url)
        validate_response(response, f"Failed to get blocklist for site {site_name}")
        return response.json().get("data", [])

    def add_allowlist_item(self, site_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Add item to allowlist."""
        path = ENDPOINTS["add-allowlist-item"].format(site_name=site_name)
        url = self._get_url(path)
        response = self.session.put(url, json=payload)
        validate_response(response, f"Failed to add item to allowlist for site {site_name}")
        return response.json()

    def add_blocklist_item(self, site_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Add item to blocklist."""
        path = ENDPOINTS["add-blocklist-item"].format(site_name=site_name)
        url = self._get_url(path)
        response = self.session.put(url, json=payload)
        validate_response(response, f"Failed to add item to blocklist for site {site_name}")
        return response.json()

    def delete_allowlist_item(self, site_name: str, item_id: str) -> None:
        """Delete item from allowlist."""
        path = ENDPOINTS["delete-allowlist-item"].format(site_name=site_name, item_id=item_id)
        url = self._get_url(path)
        response = self.session.delete(url)
        validate_response(response, f"Failed to delete allowlist item {item_id}")

    def delete_blocklist_item(self, site_name: str, item_id: str) -> None:
        """Delete item from blocklist."""
        path = ENDPOINTS["delete-blocklist-item"].format(site_name=site_name, item_id=item_id)
        url = self._get_url(path)
        response = self.session.delete(url)
        validate_response(response, f"Failed to delete blocklist item {item_id}")

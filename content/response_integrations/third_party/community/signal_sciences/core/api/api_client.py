from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from TIPCommon.base.interfaces import Apiable

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
        path = path.lstrip('/')
        return f"{self.api_root.rstrip('/')}/api/v0/corps/{self.corp_name}/{path}"

    def test_connectivity(self) -> None:
        """Test API connectivity by fetching the corp details."""
        url = self._get_url("")
        response = self.session.get(url)
        validate_response(response, "Failed to connect to Signal Sciences")

    def list_sites(self, limit: int = 100, page: int = 1) -> list[dict[str, Any]]:
        """List sites in the corporation."""
        url = self._get_url("sites")
        params = {"limit": limit, "page": page}
        response = self.session.get(url, params=params)
        validate_response(response, "Failed to list sites")
        return response.json().get("data", [])

    def get_whitelist(self, site_name: str) -> list[dict[str, Any]]:
        """Get allowlist for a site."""
        url = self._get_url(f"sites/{site_name}/whitelist")
        response = self.session.get(url)
        validate_response(response, f"Failed to get whitelist for site {site_name}")
        return response.json().get("data", [])

    def get_blacklist(self, site_name: str) -> list[dict[str, Any]]:
        """Get blocklist for a site."""
        url = self._get_url(f"sites/{site_name}/blacklist")
        response = self.session.get(url)
        validate_response(response, f"Failed to get blacklist for site {site_name}")
        return response.json().get("data", [])

    def add_whitelist_item(self, site_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Add item to allowlist."""
        url = self._get_url(f"sites/{site_name}/whitelist")
        response = self.session.put(url, json=payload)
        validate_response(response, f"Failed to add item to whitelist for site {site_name}")
        return response.json()

    def add_blacklist_item(self, site_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Add item to blocklist."""
        url = self._get_url(f"sites/{site_name}/blacklist")
        response = self.session.put(url, json=payload)
        validate_response(response, f"Failed to add item to blacklist for site {site_name}")
        return response.json()

    def delete_whitelist_item(self, site_name: str, item_id: str) -> None:
        """Delete item from allowlist."""
        url = self._get_url(f"sites/{site_name}/whitelist/{item_id}")
        response = self.session.delete(url)
        validate_response(response, f"Failed to delete whitelist item {item_id}")

    def delete_blacklist_item(self, site_name: str, item_id: str) -> None:
        """Delete item from blocklist."""
        url = self._get_url(f"sites/{site_name}/blacklist/{item_id}")
        response = self.session.delete(url)
        validate_response(response, f"Failed to delete blacklist item {item_id}")

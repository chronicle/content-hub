from urllib.parse import urljoin

import requests

from .constants import (
    ALLOW_LIST_ENDPOINT,
    ALLOW_LIST_ITEM_ENDPOINT,
    API_BASE_PATH,
    BLOCK_LIST_ENDPOINT,
    BLOCK_LIST_ITEM_ENDPOINT,
    GET_CORP_ENDPOINT,
    LIMIT_SITES_PARAM,
    LIST_SITES_ENDPOINT,
)


class SignalSciencesManager:
    def __init__(
        self, api_root: str, email: str, api_token: str, corp_name: str, verify_ssl: bool = True
    ):
        self.api_root = api_root if api_root.endswith("/") else f"{api_root}/"
        self.verify_ssl = verify_ssl
        self.email = email
        self.api_token = api_token
        self.corp_name = corp_name

        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self.session.headers.update({
            "x-api-user": self.email,
            "x-api-token": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _get_full_url(self, endpoint: str, **kwargs) -> str:
        """
        Constructs the full URL for a given endpoint.
        """
        path = endpoint.format(**kwargs).lstrip("/")
        base_path = API_BASE_PATH.lstrip("/")
        return urljoin(self.api_root, f"{base_path}/{path}")

    def test_connectivity(self) -> None:
        """
        Tests connectivity to the Signal Sciences API by hitting the corps endpoint.

        Raises:
            requests.exceptions.HTTPError: If the request fails (e.g., unauthorized).
        """
        url = self._get_full_url(GET_CORP_ENDPOINT, corp_name=self.corp_name)
        response = self.session.get(url)
        response.raise_for_status()

    def _add_ip_to_list(
        self, endpoint: str, site_name: str, ip_address: str, note: str = ""
    ) -> dict:
        url = self._get_full_url(endpoint, corp_name=self.corp_name, site_name=site_name)
        payload = {"source": ip_address, "note": note if note else "Added via SOAR"}
        response = self.session.put(url, json=payload)
        response.raise_for_status()
        return response.json()

    def _get_list(self, endpoint: str, site_name: str) -> list[dict]:
        url = self._get_full_url(endpoint, corp_name=self.corp_name, site_name=site_name)
        response = self.session.get(url)
        response.raise_for_status()
        return response.json().get("data", [])

    def _remove_ip_from_list(self, endpoint: str, site_name: str, item_id: str) -> None:
        url = self._get_full_url(
            endpoint, corp_name=self.corp_name, site_name=site_name, item_id=item_id
        )
        response = self.session.delete(url)
        response.raise_for_status()

    def add_ip_to_allowlist(self, site_name: str, ip_address: str, note: str = "") -> dict:
        return self._add_ip_to_list(ALLOW_LIST_ENDPOINT, site_name, ip_address, note)

    def get_allowlists(self, site_name: str) -> list[dict]:
        return self._get_list(ALLOW_LIST_ENDPOINT, site_name)

    def remove_ip_from_allowlist(self, site_name: str, item_id: str) -> None:
        self._remove_ip_from_list(ALLOW_LIST_ITEM_ENDPOINT, site_name, item_id)

    def add_ip_to_blocklist(self, site_name: str, ip_address: str, note: str = "") -> dict:
        return self._add_ip_to_list(BLOCK_LIST_ENDPOINT, site_name, ip_address, note)

    def get_blocklists(self, site_name: str) -> list[dict]:
        return self._get_list(BLOCK_LIST_ENDPOINT, site_name)

    def remove_ip_from_blocklist(self, site_name: str, item_id: str) -> None:
        self._remove_ip_from_list(BLOCK_LIST_ITEM_ENDPOINT, site_name, item_id)

    def get_sites(self, max_records: int = 50) -> list[dict]:
        """
        Lists all sites in the corporation with automatic pagination.
        """
        url = self._get_full_url(LIST_SITES_ENDPOINT, corp_name=self.corp_name)
        return self._paginate_results(url, max_records=max_records)

    def _paginate_results(
        self, url: str, params: dict | None = None, max_records: int = 50
    ) -> list[dict]:
        """
        Generic pagination logic for Signal Sciences API (using page/limit).
        """
        if params is None:
            params = {}

        params.setdefault("limit", LIMIT_SITES_PARAM)
        page = 1
        all_results = []

        while True:
            params["page"] = page
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json().get("data", [])
            if not data:
                break

            all_results.extend(data)

            if max_records > 0 and len(all_results) >= max_records:
                return all_results[:max_records]

            if len(data) < params["limit"]:
                break

            page += 1

        return all_results

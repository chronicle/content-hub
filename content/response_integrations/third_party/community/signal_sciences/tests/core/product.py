from __future__ import annotations

import dataclasses

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class SignalSciences:
    corps: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    sites: dict[str, list[SingleJson]] = dataclasses.field(default_factory=dict)
    allowlists: dict[str, dict[str, list[SingleJson]]] = dataclasses.field(default_factory=dict)
    blocklists: dict[str, dict[str, list[SingleJson]]] = dataclasses.field(default_factory=dict)

    def get_corp(self, corp_name: str) -> SingleJson:
        if corp_name not in self.corps:
            raise Exception("Corporation not found")
        return self.corps[corp_name]

    def add_corp(self, corp_name: str, details: SingleJson) -> None:
        self.corps[corp_name] = details

    def get_sites(self, corp_name: str) -> list[SingleJson]:
        return self.sites.get(corp_name, [])

    def add_site(self, corp_name: str, site_details: SingleJson) -> None:
        if corp_name not in self.sites:
            self.sites[corp_name] = []
        self.sites[corp_name].append(site_details)

    def get_allowlist(self, corp_name: str, site_name: str) -> list[SingleJson]:
        return self.allowlists.get(corp_name, {}).get(site_name, [])

    def add_ip_to_allowlist(
        self, corp_name: str, site_name: str, ip_address: str, note: str
    ) -> SingleJson:
        if corp_name not in self.allowlists:
            self.allowlists[corp_name] = {}
        if site_name not in self.allowlists[corp_name]:
            self.allowlists[corp_name][site_name] = []

        item = {
            "id": f"allow-{ip_address}",
            "source": ip_address,
            "note": note,
            "expires": "",
            "createdBy": "test-user",
            "created": "2024-12-16T15:13:40Z",
        }
        self.allowlists[corp_name][site_name].append(item)
        return item

    def remove_ip_from_allowlist(self, corp_name: str, site_name: str, item_id: str) -> None:
        if corp_name in self.allowlists and site_name in self.allowlists[corp_name]:
            self.allowlists[corp_name][site_name] = [
                item for item in self.allowlists[corp_name][site_name] if item["id"] != item_id
            ]

    def get_blocklist(self, corp_name: str, site_name: str) -> list[SingleJson]:
        return self.blocklists.get(corp_name, {}).get(site_name, [])

    def add_ip_to_blocklist(
        self, corp_name: str, site_name: str, ip_address: str, note: str
    ) -> SingleJson:
        if corp_name not in self.blocklists:
            self.blocklists[corp_name] = {}
        if site_name not in self.blocklists[corp_name]:
            self.blocklists[corp_name][site_name] = []

        item = {
            "id": f"block-{ip_address}",
            "source": ip_address,
            "note": note,
            "expires": "",
            "createdBy": "test-user",
            "created": "2024-12-16T15:13:40Z",
        }
        self.blocklists[corp_name][site_name].append(item)
        return item

    def remove_ip_from_blocklist(self, corp_name: str, site_name: str, item_id: str) -> None:
        if corp_name in self.blocklists and site_name in self.blocklists[corp_name]:
            self.blocklists[corp_name][site_name] = [
                item for item in self.blocklists[corp_name][site_name] if item["id"] != item_id
            ]

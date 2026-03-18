from __future__ import annotations

import dataclasses
from typing import Any

@dataclasses.dataclass(slots=True)
class SignalSciencesProduct:
    sites: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    whitelist: dict[str, list[dict[str, Any]]] = dataclasses.field(default_factory=dict)
    blacklist: dict[str, list[dict[str, Any]]] = dataclasses.field(default_factory=dict)

    def get_sites(self) -> dict[str, Any]:
        return {"data": self.sites}

    def add_site(self, site: dict[str, Any]) -> None:
        self.sites.append(site)

    def get_whitelist(self, site_name: str) -> dict[str, Any]:
        return {"data": self.whitelist.get(site_name, [])}

    def get_blacklist(self, site_name: str) -> dict[str, Any]:
        return {"data": self.blacklist.get(site_name, [])}

    def add_whitelist_item(self, site_name: str, item: dict[str, Any]) -> dict[str, Any]:
        if site_name not in self.whitelist:
            self.whitelist[site_name] = []
        if "id" not in item:
            item["id"] = f"wl_{len(self.whitelist[site_name]) + 1}"
        self.whitelist[site_name].append(item)
        return item

    def add_blacklist_item(self, site_name: str, item: dict[str, Any]) -> dict[str, Any]:
        if site_name not in self.blacklist:
            self.blacklist[site_name] = []
        if "id" not in item:
            item["id"] = f"bl_{len(self.blacklist[site_name]) + 1}"
        self.blacklist[site_name].append(item)
        return item

    def delete_whitelist_item(self, site_name: str, item_id: str) -> None:
        if site_name in self.whitelist:
            self.whitelist[site_name] = [i for i in self.whitelist[site_name] if i.get("id") != item_id]

    def delete_blacklist_item(self, site_name: str, item_id: str) -> None:
        if site_name in self.blacklist:
            self.blacklist[site_name] = [i for i in self.blacklist[site_name] if i.get("id") != item_id]

from __future__ import annotations
from .datamodels import *


class IBossParser:

    def get_auth_token(self, raw_json):
        return raw_json.get("token")

    def get_cookie(self, raw_json):
        return f'XSRF-TOKEN={raw_json.get("uid")}&{raw_json.get("sessionId")}'

    def get_entries(self, raw_json):
        return [
            self.build_entries_object(entry_json)
            for entry_json in raw_json.get("entries", [])
        ]

    def build_entries_object(self, entry_json):
        return Entry(
            raw_data=entry_json,
            url=entry_json.get("url"),
            priority=entry_json.get("priority"),
            weight=entry_json.get("weight"),
            direction=entry_json.get("direction"),
            start_port=entry_json.get("startPort"),
            end_port=entry_json.get("endPort"),
            note=entry_json.get("note"),
            is_regex=entry_json.get("isRegex"),
        )

    def custom_type_from_settings_raw_json(self, raw_json):
        return raw_json.get("customType")

    def get_account_settings_id_and_headers(self, raw_json, cookies):
        return (
            raw_json.get("selectedAccountSettingsId", ""),
            cookies.get("XSRF-TOKEN", ""),
            cookies.get("JSESSIONID", ""),
        )

    def get_nodes(self, raw_json):
        return [self.get_node(node) for node in raw_json]

    def get_node(self, raw_json):
        return Node(
            raw_data=raw_json,
            node_name=raw_json.get("nodeName"),
            public_fqdn=raw_json.get("publicFqdn"),
        )

    def prepare_master_admin_interface_dns(self, raw_json):

        for cluster in raw_json:
            if cluster.get("productFamily") == "swg":
                for member in cluster.get("members"):
                    if member.get("primary") == 1:
                        return member.get("cloudNode", {}).get(
                            "masterAdminInterfaceDns"
                        )

        raise Exception("Cloud Node ID can't be found.")

    def build_url_object(self, raw_json):
        return URL(
            raw_data=raw_json,
            action=raw_json.get("action"),
            categories=raw_json.get("categories"),
            message=raw_json.get("message"),
        )

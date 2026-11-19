from __future__ import annotations
from typing import Optional
from TIPCommon import dict_to_flat, add_prefix_to_dict

from automox.core.constants import ENRICHMENT_PREFIX

import json


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def as_json(self):
        return self.raw_data


class Policy(BaseModel):
    def __init__(
        self,
        raw_data,
        id: int = None,
        name: str = None,
        policy_type_name: str = None,
        status: str = None,
        notes: str = None,
    ):
        super().__init__(raw_data)
        self.id = id
        self.name = name
        self.type = policy_type_name
        self.status = status
        self.notes = notes

    def as_csv(self):
        return {
            "Name": self.name,
            "Type": self.type,
            "Id": self.id,
            "Status": self.status,
            "Notes": self.notes,
        }


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        id: int = None,
        ip_addrs_private: str = None,
        display_name: str = None,
        connected: bool = None,
    ):
        super().__init__(raw_data)

        self.raw_data = raw_data
        self.id = id
        self.display_name = display_name
        self.ip_addrs_private = ip_addrs_private
        self.connected = connected

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

    def get_enrichment_data(self):
        enrichment_data = {
            "id": self.id,
            "agent_version": self.raw_data.get("agent_version"),
            "compliant": self.raw_data.get("compliant"),
            "connected": self.connected,
            "create_time": self.raw_data.get("create_time"),
            "custom_name": self.raw_data.get("custom_name"),
            "ip_addrs_private": ",".join(self.raw_data.get("ip_addrs_private", [])),
            "last_disconnect_time": self.raw_data.get("last_disconnect_time"),
            "last_logged_in_user": self.raw_data.get("last_logged_in_user"),
            "last_update_time": self.raw_data.get("last_update_time"),
            "os": f"{self.raw_data.get('os_family')} {self.raw_data.get('os_name')} {self.raw_data.get('os_version')}",
            "pending_patches": self.raw_data.get("pending_patches"),
            "tags": ",".join(self.raw_data.get("tags", [])),
        }
        enrichment_data = dict_to_flat(
            {
                key: value
                for key, value in enrichment_data.items()
                if (value not in [None, "", []])
            }
        )
        return enrichment_data

    def as_enrichment_data(self):
        enrichment_data = self.get_enrichment_data()
        enrichment_data = add_prefix_to_dict(enrichment_data, ENRICHMENT_PREFIX)
        return enrichment_data

    def as_table(self):
        # A workaround around commas inside the csv fields (e.g. tags, ip_addrs_private)
        return {
            key: value.replace(",", ";")
            for key, value in self.get_enrichment_data().items()
        }


class QueueObjectCommand:
    def __init__(
        self,
        raw_data,
        id: int = None,
        server_id: int = None,
        command_id: int = None,
        organization_id: int = None,
        args: str = None,
        exec_time: str = None,
        response: Optional[str] = None,
        response_time: str = None,
        policy_id: int = None,
        agent_command_type: int = None,
        command_type_name: str = None,
    ):
        self.raw_data = raw_data
        self.id = id
        self.server_id = server_id
        self.command_id = command_id
        self.organization_id = organization_id
        self.args = args
        self.exec_time = exec_time
        self.response = response
        self.response_time = response_time
        self.policy_id = policy_id
        self.agent_command_type = agent_command_type
        self.command_type_name = command_type_name

    def as_json(self):
        copy_raw_data = self.raw_data.copy()
        copy_raw_data["response"] = json.loads(self.response)
        return copy_raw_data


class Patch(BaseModel):
    def __init__(
        self, raw_data, id: int = None, installed: bool = None, ignored: bool = None
    ):
        super().__init__(raw_data)
        self.id = id
        self.installed = installed
        self.ignored = ignored

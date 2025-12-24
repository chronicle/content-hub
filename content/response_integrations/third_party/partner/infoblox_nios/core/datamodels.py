from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from TIPCommon.transformation import dict_to_flat


class BaseModel(object):
    """
    Base model for all Infoblox datamodels.
    """

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        self.raw_data = raw_data

    def to_json(self) -> Dict[str, Any]:
        return self.raw_data

    def to_csv(self) -> Dict[str, Any]:
        return dict_to_flat(self.to_json())


class RPZRule(BaseModel):
    """
    RPZ Rule model.
    """

    def __init__(self, raw_data: Dict[str, Any], output_fields: Optional[List[str]] = None) -> None:
        super().__init__(raw_data)
        self.raw_data = raw_data
        self.reference_id = raw_data.get("_ref")
        self.name = raw_data.get("name")
        self.canonical = raw_data.get("canonical")
        self.view = raw_data.get("view")
        self.output_fields = output_fields

    def to_csv(self) -> Dict[str, Any]:
        base_fields = {"_ref", "name", "canonical", "view"}
        payload = {
            "Reference ID": self.reference_id,
            "Name": self.name,
            "Canonical": self.canonical,
            "View": self.view,
        }

        if self.output_fields:
            extra_fields = [field for field in self.output_fields if field not in base_fields]
            for field in extra_fields[:3]:
                payload[field.replace("_", " ").capitalize()] = self.raw_data.get(field)

        return payload


class IPLookup(BaseModel):
    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.ip_address = raw_data.get("ip_address")
        self.status = raw_data.get("status")
        self.ref = raw_data.get("_ref")
        self.types = raw_data.get("types", [])
        self.network = raw_data.get("network")
        self.mac_address = raw_data.get("mac_address") or raw_data.get("duid")
        self.names = raw_data.get("names", [])
        self.usage = raw_data.get("usage", [])
        self.comment = raw_data.get("comment")
        self.is_conflict = raw_data.get("is_conflict")
        self.extattrs = raw_data.get("extattrs", {})

    def to_csv(self) -> Dict[str, Any]:
        return {
            "Reference ID": self.ref,
            "IP Address": self.ip_address,
            "Status": self.status,
            "Types": ", ".join(self.types),
            "Network": self.network,
            "MAC Address/DUID": self.mac_address,
            "Names": ", ".join(self.names),
            "Usage": ", ".join(self.usage),
            "Comment": self.comment,
            "Is Conflict": self.is_conflict,
            "Extended Attributes": json.dumps(self.extattrs),
        }


class RPZone(BaseModel):
    """
    RP Zone model for output formatting.
    """

    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.reference_id = raw_data.get("_ref")
        self.fqdn = raw_data.get("fqdn")
        self.rpz_policy = raw_data.get("rpz_policy")
        self.rpz_severity = raw_data.get("rpz_severity")
        self.rpz_type = raw_data.get("rpz_type")
        self.comment = raw_data.get("comment")
        self.disable = raw_data.get("disable")
        self.substitute_name = raw_data.get("substitute_name")
        self.rpz_priority = raw_data.get("rpz_priority")

    def to_csv(self) -> Dict[str, Any]:
        return {
            "Reference ID": self.reference_id,
            "FQDN": self.fqdn,
            "RPZ Policy": self.rpz_policy,
            "RPZ Severity": self.rpz_severity,
            "RPZ Type": self.rpz_type,
            "Comment": self.comment,
            "Disable": self.disable,
            "Substitute Name": self.substitute_name,
            "RPZ Priority": self.rpz_priority,
        }


class Network(BaseModel):
    """
    Network model.
    """

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.raw_data = raw_data
        self.reference_id = raw_data.get("_ref")
        self.network = raw_data.get("network")
        self.network_view = raw_data.get("network_view")
        self.network_container = raw_data.get("network_container")
        self.comment = raw_data.get("comment")
        self.utilization = raw_data.get("utilization")
        self.authority = raw_data.get("authority")

    def to_csv(self) -> Dict[str, Any]:
        return {
            "Reference ID": self.reference_id,
            "Network": self.network,
            "Network View": self.network_view,
            "Network Container": self.network_container,
            "Comment": self.comment,
            "Utilization": self.utilization,
            "Authority": self.authority,
        }


class RPZRuleRecord(BaseModel):
    def __init__(self, raw_data: Dict[str, Any], object_type: str) -> None:
        super().__init__(raw_data)
        self.raw_data = raw_data
        self.reference_id = raw_data.get("_ref")
        self.object_type = object_type
        self.name = raw_data.get("name")
        self.comment = raw_data.get("comment")
        self.disable = raw_data.get("disable")
        self.view = raw_data.get("view")
        self.rp_zone = raw_data.get("rp_zone")

    def _common(self) -> Dict[str, Any]:
        return {
            "Reference ID": self.reference_id,
            "Object Type": self.object_type,
            "Name": self.name,
            "Comment": self.comment,
            "Disable": self.disable,
            "View": self.view,
            "RP Zone": self.rp_zone,
        }

    def create_txt_rule_csv(self) -> Dict[str, Any]:
        return {
            **self._common(),
            "Text": self.raw_data.get("text"),
        }

    def create_a_rule_csv(self) -> Dict[str, Any]:
        return {
            **self._common(),
            "IPv4 Address": self.raw_data.get("ipv4addr"),
        }

    def create_aaaa_rule_csv(self) -> Dict[str, Any]:
        return {
            **self._common(),
            "IPv6 Address": self.raw_data.get("ipv6addr"),
        }

    def create_naptr_rule_csv(self) -> Dict[str, Any]:
        return {**self._common(), "Replacement": self.raw_data.get("replacement")}

    def create_srv_rule_csv(self) -> Dict[str, Any]:
        return {
            **self._common(),
            "Target": self.raw_data.get("target"),
            "Port": self.raw_data.get("port"),
            "Priority": self.raw_data.get("priority"),
            "Weight": self.raw_data.get("weight"),
        }

    def create_mx_rule_csv(self) -> Dict[str, Any]:
        return {
            **self._common(),
            "Mail Exchanger": self.raw_data.get("mail_exchanger"),
            "Preference": self.raw_data.get("preference"),
        }

    def create_ptr_rule_csv(self) -> Dict[str, Any]:
        return {**self._common(), "PTR Dname": self.raw_data.get("ptrdname")}


class DHCPLeaseLookup(BaseModel):
    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.ref = raw_data.get("_ref")
        self.ip_address = raw_data.get("address")
        self.hardware = raw_data.get("hardware")
        self.client_hostname = raw_data.get("client_hostname")
        self.binding_state = raw_data.get("binding_state")
        self.ends = raw_data.get("ends")
        self.fingerprint = raw_data.get("fingerprint")
        self.network = raw_data.get("network")

    def to_csv(self) -> Dict[str, Any]:
        return {
            "Reference ID": self.ref,
            "IP Address": self.ip_address,
            "Hardware": self.hardware,
            "Client Hostname": self.client_hostname,
            "Binding State": self.binding_state,
            "Ends": self.ends,
            "Fingerprint": self.fingerprint,
            "Network": self.network,
        }


class Host(BaseModel):
    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.ref = raw_data.get("_ref")
        self.name = raw_data.get("name")
        self.view = raw_data.get("view")
        self.zone = raw_data.get("zone")
        self.disable = raw_data.get("disable")
        self.comment = raw_data.get("comment")
        self.network_view = raw_data.get("network_view")
        self.configure_for_dns = raw_data.get("configure_for_dns")
        self.extattrs = raw_data.get("extattrs", {})
        self.ipv4addrs = raw_data.get("ipv4addrs", [])
        self.ipv6addrs = raw_data.get("ipv6addrs", [])

    def to_csv(self) -> Dict[str, Any]:
        return {
            "Reference ID": self.ref,
            "Name": self.name,
            "View": self.view,
            "Zone": self.zone,
            "Disabled": self.disable,
            "Comment": self.comment,
            "Network View": self.network_view,
            "Configure For DNS": self.configure_for_dns,
            "Extended Attributes": json.dumps(self.extattrs),
            "IPv4 Addresses": ", ".join([addr["ipv4addr"] for addr in self.ipv4addrs]),
            "IPv6 Addresses": ", ".join([addr["ipv6addr"] for addr in self.ipv6addrs]),
        }


class RPZCNAMERule(BaseModel):
    def __init__(self, raw_data: Dict[str, Any], rule_type: str) -> None:
        super().__init__(raw_data)
        self.ref = raw_data.get("_ref")
        self.disabled = raw_data.get("disable")
        self.canonical = raw_data.get("canonical")
        self.name = raw_data.get("name")
        self.rp_zone = raw_data.get("rp_zone")
        self.view = raw_data.get("view")
        self.rule_type = rule_type

    def to_csv(self) -> Dict[str, Any]:
        return {
            "Reference ID": self.ref,
            "Disabled": self.disabled,
            "Canonical": self.canonical,
            "Rule Type": self.rule_type,
            "Name": self.name,
            "RP Zone": self.rp_zone,
            "View": self.view,
        }

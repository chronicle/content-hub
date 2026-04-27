from __future__ import annotations
import copy

from TIPCommon import dict_to_flat, add_prefix_to_dict

from .constants import ENDPOINT_INSIGHT_TEMPLATE, ENRICHMENT_PREFIX, GREEN, RED


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())


class EndpointInfo(BaseModel):
    """
    Endpoint information data model
    """

    def __init__(
        self,
        raw_data,
        ip_address=None,
        mac_address=None,
        onsite=None,
        guest_corporate_state=None,
        fingerprint=None,
        vendor=None,
        classification=None,
        agent_version=None,
        online=None,
    ):
        super(EndpointInfo, self).__init__(raw_data)
        self.ip_address = ip_address
        self.mac_address = mac_address
        self.onsite = onsite
        self.guest_corporate_state = guest_corporate_state
        self.fingerprint = fingerprint
        self.vendor = vendor
        self.classification = classification
        self.agent_version = agent_version
        self.online = online

    def to_enrichment(self, prefix=ENRICHMENT_PREFIX):
        enrichment_table = {
            "ip": self.ip_address,
            "mac": self.mac_address,
            "onsite": self.onsite,
            "guest_corporate_state": self.guest_corporate_state,
            "fingerprint": self.fingerprint,
            "vendor": self.vendor,
            "classification": self.classification,
            "agent_version": self.agent_version,
            "online": self.online,
        }
        return add_prefix_to_dict(dict_to_flat(enrichment_table), prefix)

    def to_csv(self):
        return [
            {"Key": key, "Value": value}
            for key, value in dict_to_flat(
                {
                    "ip": self.ip_address,
                    "mac": self.mac_address,
                    "onsite": self.onsite,
                    "guest_corporate_state": self.guest_corporate_state,
                    "fingerprint": self.fingerprint,
                    "vendor": self.vendor,
                    "classification": self.classification,
                    "agent_version": self.agent_version,
                    "online": self.online,
                }
            ).items()
        ]

    def to_insight(self, entity_identifier=None):
        return ENDPOINT_INSIGHT_TEMPLATE.format(
            endpoint_identifier=entity_identifier,
            is_online_color=(
                GREEN if self.online and self.online.lower() == "true" else RED
            ),
            is_online=(
                self.online.title()
                if self.online and isinstance(self.online, str)
                else self.online
            ),
            ip_address=self.ip_address,
            mac_address=self.mac_address,
            fingerprint=self.fingerprint,
            classification=self.classification,
            agent_version=self.agent_version,
        )

    def to_json(self):
        raw_data = copy.deepcopy(self.raw_data)
        return raw_data.get("host", {})

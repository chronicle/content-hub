from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from symantec_escc.core.UtilsManager import convert_list_to_comma_string
from symantec_escc.core.constants import (
    BLOCKED_STATE,
    ENDPOINT_LINK_FORMAT,
    BLOCKED_DESC,
    UNKNOWN_DESC,
    AT_RISK_STATUS,
    BAD_REPUTATION,
    GOOD_REPUTATION,
)


GREEN_COLOR = "#339966"
RED_COLOR = "#ff0000"
BLACK_COLOR = "#000000"


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class DeviceGroup(BaseModel):
    def __init__(self, raw_data, id, name):
        super(DeviceGroup, self).__init__(raw_data)
        self.id = id
        self.name = name

    def to_csv(self):
        return dict_to_flat({"ID": self.id, "Name": self.name})


class Device(BaseModel):
    def __init__(
        self, raw_data, id, name, os_name, host, domain, adapters, device_status, user
    ):
        super(Device, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.os_name = os_name
        self.host = host
        self.domain = domain
        self.adapters = adapters
        self.device_status = device_status
        self.link = ENDPOINT_LINK_FORMAT.format(id=self.id)
        self.user = user

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self._get_enrichment_data())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def _get_enrichment_data(self):
        return {
            "id": self.id,
            "os": self.os_name,
            "hostname": self.host,
            "domain": self.domain,
            "ips": convert_list_to_comma_string(
                [adapter.get("ipv4Address") for adapter in self.adapters]
            ),
            "mac": convert_list_to_comma_string(
                [adapter.get("addr") for adapter in self.adapters]
            ),
            "status": self.device_status,
            "link": self.link,
        }

    def to_csv(self):
        data = self._get_enrichment_data()
        data.pop("link", None)
        return data

    def to_insight(self, identifier):
        content = f"<br><strong>Endpoint:</strong> {identifier}<br>"
        content += "<body>"
        status_color = (
            RED_COLOR if self.device_status == AT_RISK_STATUS else GREEN_COLOR
        )
        content += (
            f'<br><strong>Status:</strong><span style="color: {status_color};"><strong>'
            f' {self.device_status  or "N/A"}</strong></span>'
        )
        content += (
            f'<br><strong>IP Address:</strong><span style="font-weight: 400;">'
            f' {convert_list_to_comma_string([adapter.get("ipv4Address") for adapter in self.adapters]) or "N/A"}'
            f"</span>"
        )
        content += (
            f'<br><strong>Mac Address:</strong><span style="font-weight: 400;">'
            f' {convert_list_to_comma_string([adapter.get("addr") for adapter in self.adapters]) or "N/A"}'
            f"</span>"
        )
        content += f'<br><strong>OS:</strong> {self.os_name  or "N/A"}'
        content += f'<br><strong>User:</strong> {self.user  or "N/A"}'
        content += f'<br><strong>Link:</strong><a href={self.link} target="_blank"> {self.link}</a>'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class EntityDetails(BaseModel):
    def __init__(
        self,
        raw_data,
        reputation,
        prevalence,
        top_countries,
        top_industries,
        first_seen,
        last_seen,
        state,
    ):
        super(EntityDetails, self).__init__(raw_data)
        self.reputation = reputation
        self.prevalence = prevalence
        self.top_countries = top_countries
        self.top_industries = top_industries
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.state = state

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self._get_enrichment_data())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def _get_enrichment_data(self):
        return {
            "reputation": self.reputation,
            "prevalence": self.prevalence,
            "countries": self.top_countries,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "industries": self.top_industries,
            "state": self.state,
        }

    def to_csv(self):
        return dict_to_flat(self._get_enrichment_data())

    def to_insight(self, identifier):
        content = f"<br><strong>Entity:</strong> {identifier}<br>"
        content += "<body>"
        reputation_color = (
            RED_COLOR
            if self.reputation == BAD_REPUTATION
            else GREEN_COLOR if self.reputation == GOOD_REPUTATION else BLACK_COLOR
        )
        content += (
            f'<br><strong>Reputation:</strong><span style="color: {reputation_color};">'
            f'<strong> {self.reputation or "N/A"}</strong></span>'
        )
        content += f'<br><strong>Prevalence:</strong> {self.prevalence or "N/A"}'
        content += f'<br><strong>First Seen:</strong> {self.first_seen or "N/A"}'
        content += f'<br><strong>Last Seen:</strong> {self.last_seen or "N/A"}'
        content += f'<br><strong>Countries:</strong> {self.top_countries or "N/A"}'
        content += f'<br><strong>Industries:</strong> {self.top_industries or "N/A"}'
        content += (
            f"<br><strong>State:</strong>"
            f" {BLOCKED_DESC if self.state == BLOCKED_STATE else UNKNOWN_DESC}"
        )
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content


class RelatedIOC(BaseModel):
    def __init__(self, raw_data, ioc_type, relation, ioc_values):
        super(RelatedIOC, self).__init__(raw_data)
        self.ioc_type = ioc_type
        self.relation = relation
        self.ioc_values = ioc_values

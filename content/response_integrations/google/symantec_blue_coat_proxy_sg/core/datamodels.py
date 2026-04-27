from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .UtilsManager import convert_list_to_comma_string


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

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class EntityInfo(BaseModel):
    def __init__(self, raw_data, raw_json_data):
        super(EntityInfo, self).__init__(raw_data)
        self.raw_json_data = raw_json_data

    def to_json(self):
        return {"raw_output": self.raw_data, **self.raw_json_data}

    def to_table(self):
        return dict_to_flat(self.raw_json_data)


class HostnameEntityInfo(EntityInfo):
    def __init__(
        self,
        raw_data,
        raw_json_data,
        official_hostname,
        resolved_addresses,
        cache_ttl,
        error,
    ):
        super(HostnameEntityInfo, self).__init__(raw_data, raw_json_data)
        self.official_hostname = official_hostname
        self.resolved_addresses = resolved_addresses
        self.cache_ttl = cache_ttl
        self.error = error

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(
            {
                "official_hostname": self.official_hostname,
                "resolved_addresses": convert_list_to_comma_string(
                    self.resolved_addresses
                ),
                "cache_ttl": self.cache_ttl,
            }
        )

        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self):
        return (
            f"<p><strong>Official Hostname: {self.official_hostname}</strong></p>"
            f"<p><strong>Resolved IP Addresses: {convert_list_to_comma_string(self.resolved_addresses)}</strong></p>"
        )


class IpEntityInfo(EntityInfo):
    def __init__(self, raw_data, raw_json_data, country):
        super(IpEntityInfo, self).__init__(raw_data, raw_json_data)
        self.country = country

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat({"country": self.country})

        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self):
        return f"<p><strong>Country: {self.country}</strong></p>"


class UrlEntityInfo(EntityInfo):
    def __init__(self, raw_data, raw_json_data, risk_level, categories, category_group):
        super(UrlEntityInfo, self).__init__(raw_data, raw_json_data)
        self.risk_level = risk_level
        self.categories = categories
        self.category_group = category_group

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(
            {
                "risk_level": self.risk_level,
                **{f"category_{key}": value for key, value in self.categories.items()},
                **{
                    f"category_group_{key}": value
                    for key, value in self.category_group.items()
                },
            }
        )

        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self):
        insight = (
            f"<p><strong>RISK LEVEL: {self.risk_level}</strong></p>"
            f"<p><strong>Categories</strong></p>"
        )

        for key, value in self.categories.items():
            insight += f"<p><strong>{key}: {value}</strong></p>"

        insight += "<p><strong>Category Groups:</strong></p>"

        for key, value in self.category_group.items():
            insight += f"<p><strong><strong>{key}: {value}</strong></strong></p>"

        insight += "<p>&nbsp;</p>"

        return insight

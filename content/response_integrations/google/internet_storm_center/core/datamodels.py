from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict


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


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        count,
        attacks,
        first_seen,
        last_seen,
        comment,
        max_risk,
        asabuse_contact,
        as_name,
        as_country,
        threat_feeds,
    ):
        super(Device, self).__init__(raw_data)
        self.count = count
        self.attacks = attacks
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.comment = comment
        self.max_risk = max_risk
        self.asabuse_contact = asabuse_contact
        self.as_name = as_name
        self.as_country = as_country
        self.threat_feeds = threat_feeds

    def to_csv(self):
        table_data = self.to_table()
        return dict_to_flat(table_data)

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(
            {key: value for key, value in self.to_table().items() if value}
        )
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_table(self):
        return {
            "count": self.count,
            "attacks": self.attacks,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "comment": self.comment,
            "maxrisk": self.max_risk,
            "asabuse_contact": self.asabuse_contact,
            "as_name": self.as_name,
            "as_country": self.as_country,
            "threatfeeds": self.threat_feeds,
        }

    def to_insight(self):
        return (
            f"<p><strong>Blocked Packets Count: </strong>{self.count or 'N/A'}"
            f"<strong><br />Amount Of Attacks: </strong>{self.attacks or 'N/A'}<br />"
            f"<strong>First Seen: </strong>{self.first_seen or 'N/A'}<br />"
            f"<strong>Last Seen: </strong>{self.last_seen or 'N/A'}<br />"
            f"<strong>Comment: </strong>{self.comment or 'N/A'}<br />"
            f"<strong>Threat Feeds:</strong> {self.threat_feeds or 'N/A'}</p><p>&nbsp;</p>"
        )

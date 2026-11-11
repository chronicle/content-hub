from __future__ import annotations
import dataclasses
from TIPCommon.transformation import dict_to_flat


class DslSearchResult:
    def __init__(self, raw_data, alert_id):
        self.raw_data = raw_data
        self.alert_id = alert_id

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.raw_data)


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    server: str
    username: str
    password: str
    jwt_token: str
    authenticate: bool
    verify_ssl: bool
    ca_certificate_file: str

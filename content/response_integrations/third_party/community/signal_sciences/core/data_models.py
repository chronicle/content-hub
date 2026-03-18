from __future__ import annotations

import dataclasses


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    email: str
    api_token: str
    corp_name: str
    verify_ssl: bool


class SampleDataModel:
    def __init__(self, raw_data: dict[str, any]):
        self.raw_data = raw_data

    def to_json(self) -> dict[str, any]:
        return self.raw_data

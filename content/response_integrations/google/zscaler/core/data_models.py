from __future__ import annotations

import dataclasses

@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    login_id: str | None = None
    api_key: str | None = None
    password: str | None = None
    verify_ssl: bool = False
    client_id: str | None = None
    client_secret: str | None = None
    login_api_root: str | None = None

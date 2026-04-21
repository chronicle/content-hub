from typing import NamedTuple


class IntegrationParameters(NamedTuple):
    host: str
    client_id: str
    client_secret: str
    verify_ssl: bool
    is_infinity: bool

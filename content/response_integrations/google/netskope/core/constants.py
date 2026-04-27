from __future__ import annotations
DEFAULT_TIME_WINDOW_SECONDS: int = 86400
ERROR_STATUS: str = "error"
MAX_CLIENTS_LIMIT_V1: int = 5000
MAX_CLIENTS_LIMIT_V2: int = 10000
MAX_EVENTS_LIMIT_V2: int = 5000
MIN_RESULTS_LIMIT: int = 1
QUARANTINE_MAX_LIMIT: int = 100
TYPES: list[str] = ["page", "application", "audit", "infrastructure"]

V1_ENDPOINTS = {
    "clients": "api/v1/clients",
    "quarantine": "api/v1/quarantine",
}

V2_ENDPOINTS = {
    "oauth_token_generate": "api/v2/platform/oauth2/token/generate",
    "application": "api/v2/events/data/application",
    "audit": "api/v2/events/data/audit",
    "infrastructure": "api/v2/events/data/infrastructure",
    "page": "api/v2/events/data/page",
    "alert": "api/v2/events/data/alert",
    "clients": "api/v2/events/datasearch/clientstatus",
    "quarantine": "api/v2/casbapi/incidents/quarantine",
    "quarantine_restore": "api/v2/casbapi/incidents/quarantine/{file_id}/restore",
    "quarantine_block": "api/v2/casbapi/incidents/quarantine/{file_id}/block",
    "download_casb_file": (
        "api/v2/casbapi/apps/{app}/instances/{instance}/files/{file_id}/content"
    ),
    "url_list": "api/v2/policy/urllist",
    "url_list_append": "api/v2/policy/urllist/{list_id}/append",
    "url_list_deploy": "api/v2/policy/urllist/deploy",
}

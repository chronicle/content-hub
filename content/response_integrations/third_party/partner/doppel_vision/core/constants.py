from __future__ import annotations

INTEGRATION_NAME: str = "DoppelVision"

API_HOST: str = "https://api.doppel.com"
OAUTH_TOKEN_URL: str = f"{API_HOST}/oauth/token"
OAUTH_AUDIENCE: str = "doppel-external"
DOPPEL_CLIENT_HEADER: str = "doppel-google-secops/8.0"

API_VERSION_V1: str = "v1"
API_VERSION_V2: str = "v2"
SUPPORTED_API_VERSIONS: tuple[str, ...] = (API_VERSION_V1, API_VERSION_V2)

DEFAULT_TOKEN_EXPIRES_IN_SECONDS: int = 86400
TOKEN_EXPIRY_BUFFER_SECONDS: int = 300
HTTP_TIMEOUT_SECONDS: float = 30
MAX_HTTP_RETRIES: int = 3

PARAM_API_VERSION: str = "API Version"
PARAM_API_KEY: str = "API Key"
PARAM_USER_API_KEY: str = "User API Key"
PARAM_ORG_CODE: str = "Organization Code"
PARAM_CLIENT_ID: str = "Client ID"
PARAM_CLIENT_SECRET: str = "Client Secret"

TOKEN_CACHE_PROPERTY_KEY: str = "doppel_oauth_token"
GLOBAL_CONTEXT_SCOPE: int = 0

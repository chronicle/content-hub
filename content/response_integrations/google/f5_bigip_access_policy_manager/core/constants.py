from __future__ import annotations
INTEGRATION_NAME = "F5BIGIPAccessPolicyManager"
INTEGRATION_DISPLAY_NAME = "F5 BIG-IP Access Policy Manager"

PING_ACTION = f"{INTEGRATION_DISPLAY_NAME} - Ping"
LIST_ACTIVE_SESSIONS_ACTION = f"{INTEGRATION_DISPLAY_NAME} - List Active Sessions"
DISCONNECT_SESSIONS_ACTION = f"{INTEGRATION_DISPLAY_NAME} - Disconnect Sessions"

TOKEN_FILE_PATH = "token.txt"
DEFAULT_ENCODING = "utf-8"

# ENDPOINTS
LOGIN_QUERY = "{}/mgmt/shared/authn/login"
UPDATE_TIMEOUT_QUERY = "{}/mgmt/shared/authz/tokens/{}"
PING_QUERY = "{}/mgmt/shared/authz/tokens"
LIST_ACTIVE_SESSIONS_QUERY = "{}/mgmt/tm/apm/access-info?$top={}"
DISCONNECT_SESSIONS_GET_QUERY = "{}/mgmt/tm/apm/access-info"
DISCONNECT_SESSIONS_DELETE_QUERY = "{}/mgmt/tm/apm/session/{}"

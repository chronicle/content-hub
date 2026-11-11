from __future__ import annotations
INTEGRATION_NAME = "HashiCorpVault"
INTEGRATION_DISPLAY_NAME = "HashiCorp Vault"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
LIST_KEY_VALUE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Key-Value Secret Keys"
READ_KEY_VALUE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Read Key-Value Secret"
LIST_AWS_ROLES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List AWS Roles"
GENERATE_AWS_CREDENTIALS_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Generate AWS Credentials"
)


ENDPOINTS = {
    "auth": "/v1/auth/userpass/login/{username}",
    "ping": "/v1/sys/host-info",
    "list_key_value": "/v1/{key_value}/metadata/{secret_path}",
    "read_key_value_secret": "/v1/{key_value}/data/{secret_path}",
    "list_aws_roles": "/v1/{key_value}/roles/",
    "generate_aws_creds": "/v1/{key_value}/creds/{role_name}",
}

RECORDS_DEFAULT_LIMIT = 50
EXPRESSION_DELIMITER = "|"
DEFAULT_TTL_SECONDS = 3600

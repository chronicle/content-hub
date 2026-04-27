from __future__ import annotations
INTEGRATION_NAME = "Snowflake"
INTEGRATION_DISPLAY_NAME = "Snowflake"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
EXECUTE_CUSTOM_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Custom Query"
EXECUTE_SIMPLE_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Simple Query"

ENDPOINTS = {
    "ping": "/api/v2/statements?async=false",
    "submit_query": "/api/v2/statements?async=true",
    "get_data": "/api/v2/statements/{query_id}",
}

EXECUTION_FINISHED = 0
EXECUTION_IN_PROGRESS = 1
ALL_FIELDS_WILDCARD = "*"
ASC_SORT_ORDER = "ASC"

from __future__ import annotations
INTEGRATION_NAME = "SumoLogicCloudSIEM"
INTEGRATION_DISPLAY_NAME = "Sumo Logic Cloud SIEM"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ADD_COMMENT_TO_INSIGHT_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add Comment To Insight"
)
ADD_TAGS_TO_INSIGHT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Add Tags To Insight"
UPDATE_INSIGHT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Insight"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Enrich Entities"
SEARCH_ENTITY_SIGNALS_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Search Entity Signals"
)

ENDPOINTS = {
    "ping": "/insights?limit=1",
    "add_comment_to_insight": "/insights/{insight_id}/comments",
    "add_tags_to_insight": "/insights/{insight_id}/tags",
    "update_assignee": "/insights/{insight_id}/assignee",
    "update_status": "/insights/{insight_id}/status",
    "get_insights": "/insights",
    "get_entity_info": "/entities",
    "get_signals": "/signals",
    "get_insight": "/insights/{insight_id}",
}

API_ROOT_SUFFIX = {"by_api_key": "/api/v1", "by_access_id": "/api/sec/v1"}

STATUS_MAPPING = {
    "Select One": "",
    "New": "New",
    "In Progress": "In Progress",
    "Closed": "Closed",
}

ASSIGNEE_TYPE_MAPPING = {"User": "USER", "Team": "TEAM"}

ASC_SORT_ORDER = "ASC"
DESC_SORT_ORDER = "DESC"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DEFAULT_SEVERITY = 5
DEFAULT_ACTION_LIMIT = 50
TIMEFRAME_MAPPING = {
    "Last Hour": {"hours": 1},
    "Last 6 Hours": {"hours": 6},
    "Last 24 Hours": {"hours": 24},
    "Last Week": "last_week",
    "Last Month": "last_month",
    "Custom": "custom",
    "5 Minutes Around Alert Time": "5 Minutes Around Alert Time",
    "30 Minutes Around Alert Time": "30 Minutes Around Alert Time",
    "1 Hour Around Alert Time": "1 Hour Around Alert Time",
}

ENTITY_TYPE_TO_QUERY = {
    "ADDRESS": "entity.ip",
    "HOSTNAME": "entity.hostname",
    "USERUNIQNAME": "entity.username",
}

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Insights Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 20
DEFAULT_MAX_LIMIT = 100
DEVICE_VENDOR = "Sumo Logic Cloud SIEM"
DEVICE_PRODUCT = "Cloud SIEM"
TACTIC_TAG_PREFIX = "_mitreAttackTactic:"
TECHNIQUE_TAG_PREFIX = "_mitreAttackTechnique:"
DISPLAY_ID_PREFIX = "SUMO_LOGIC_CLOUD_SIEM_"
TIMESTAMP_KEY = "timestamp_ms"

POSSIBLE_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SUMOLOGIC_SEVERITY_MAPPING = {"CRITICAL": 100, "HIGH": 80, "MEDIUM": 60, "LOW": 40}

ENRICHMENT_PREFIX = "SumoLogicCloudSIEM"

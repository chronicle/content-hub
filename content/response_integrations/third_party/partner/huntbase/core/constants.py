from __future__ import annotations

INTEGRATION_NAME = "Huntbase"
INTEGRATION_VERSION = "1.0"
USER_AGENT = f"Huntbase-GoogleSecOps-SOAR/{INTEGRATION_VERSION}"

# Script names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
START_HUNT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Start Hunt"
GET_HUNT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Hunt"
ASK_SCOUT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ask Scout"
ADD_TO_WATCHLIST_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add To Watchlist"
LIST_PENDING_APPROVALS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Pending Approvals"
FINDINGS_CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_NAME} - Findings Connector"

# Integration configuration parameter names
PARAM_API_ROOT = "API Root"
PARAM_API_KEY = "API Key"
PARAM_VERIFY_SSL = "Verify SSL"

DEFAULT_API_ROOT = "https://app.huntbase.io/api/v1"

# HTTP behaviour
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
MAX_RETRY_AFTER_SECONDS = 30
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# Huntbase REST routes, relative to the API Root (".../api/v1").
# Kept in one place so they can follow the backend contract.
ENDPOINTS = {
    "ping": "/access/vocabulary",
    "intel_lookup": "/intel/lookup",
    "intel_sightings": "/intel/sightings",
    "entity_by_value": "/entities/by-value",
    "entity": "/entities/{entity_id}",
    "start_hunt": "/hunts/auto",
    "hunt": "/sessions/{hunt_id}",
    "hunt_findings": "/sessions/{hunt_id}/findings",
    "hunt_verdicts": "/sessions/{hunt_id}/verdicts",
    "findings": "/findings",
    "insights": "/insights",
    "scout_jobs": "/agents/scout/jobs",
    "scout_job": "/agents/scout/jobs/{job_id}",
    "watchlists": "/intel/watchlists",
    "watchlist_values": "/intel/watchlists/{watchlist_id}/values",
    "proposals": "/agents/scout/proposals",
}

# Huntbase app deep-link paths, relative to the app root.
APP_PATHS = {
    "hunt": "/hunts/{hunt_id}",
    "finding": "/findings/{finding_id}",
    "insight": "/insights/{insight_id}",
    "entity": "/entities/{entity_id}",
    "indicator": "/intelligence/indicators/{indicator_id}",
    "approvals": "/needs-you?lane=approvals",
    "approval": "/needs-you?lane=approvals&proposal={proposal_id}",
}
LINK_SOURCE = "google_secops"

# Enrichment
ENRICHMENT_PREFIX = "HB"
INTEL_LOOKUP_BATCH_SIZE = 100
ENTITY_SEARCH_LIMIT = 5
DEFAULT_SUSPICIOUS_THRESHOLD = 70


# Hunts
HUNT_SESSION_MODES = ("guided", "supervised", "autonomous")
MAX_HUNT_SEED_VALUES = 20
SCOUT_INITIATIVES = ("low", "medium")
MAX_SCOUT_QUESTION_CHARS = 4000
EXTERNAL_REF_SOURCE = "google_secops"
DEFAULT_HUNT_SESSION_MODE = "supervised"
HUNT_TERMINAL_STATUSES = frozenset({"closed", "concluded", "completed", "resolved", "archived"})

# Scout
SCOUT_TERMINAL_OK = frozenset({"succeeded", "completed", "done"})
SCOUT_TERMINAL_FAILED = frozenset({"failed", "error", "cancelled", "canceled", "expired", "lost"})

# Connector
DEFAULT_MAX_ALERTS_PER_CYCLE = 50
DEFAULT_MAX_HOURS_BACKWARDS = 24
CONNECTOR_PAGE_SIZE = 50
CONNECTOR_TEST_RUN_MAX_ALERTS = 5
WATERMARK_KEY = "huntbase_watermarks"
PROCESSED_IDS_KEY = "huntbase_processed_ids"
MAX_STORED_IDS = 2000
SOURCE_FINDINGS = "Findings"
SOURCE_INSIGHTS = "Insights"
SOURCE_BOTH = "Findings and Insights"
DEFAULT_FINDING_DISPOSITIONS = ("confirmed",)
DEFAULT_INSIGHT_MIN_SEVERITY = "high"
# GET /insights filters on event time, not ingest time: re-read this far behind the watermark
INSIGHT_OVERLAP_MINUTES = 60
DEVICE_PRODUCT = "Huntbase"
DEVICE_VENDOR = "Huntbase"
RULE_GENERATOR_FINDING = "Huntbase Finding"
RULE_GENERATOR_INSIGHT = "Huntbase Insight"

# SOAR alert priority values
PRIORITY_INFO = -1
PRIORITY_LOW = 40
PRIORITY_MEDIUM = 60
PRIORITY_HIGH = 80
PRIORITY_CRITICAL = 100
SEVERITY_TO_PRIORITY = {
    "informational": PRIORITY_INFO,
    "info": PRIORITY_INFO,
    "unknown": PRIORITY_INFO,
    "low": PRIORITY_LOW,
    "medium": PRIORITY_MEDIUM,
    "high": PRIORITY_HIGH,
    "critical": PRIORITY_CRITICAL,
    "fatal": PRIORITY_CRITICAL,
}
SEVERITY_ORDER = ("informational", "low", "medium", "high", "critical")

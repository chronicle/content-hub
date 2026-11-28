from __future__ import annotations

INTEGRATION_NAME: str = "Huntbase"
INTEGRATION_VERSION: str = "1.0"
USER_AGENT: str = f"Huntbase-GoogleSecOps-SOAR/{INTEGRATION_VERSION}"

# Script names
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Enrich Entities"
START_HUNT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Start Hunt"
GET_HUNT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Hunt"
ASK_SCOUT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ask Scout"
ADD_TO_WATCHLIST_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add To Watchlist"
LIST_PENDING_APPROVALS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - List Pending Approvals"
FINDINGS_CONNECTOR_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Findings Connector"

# Integration configuration parameter names
PARAM_API_ROOT: str = "API Root"
PARAM_API_KEY: str = "API Key"
PARAM_VERIFY_SSL: str = "Verify SSL"

DEFAULT_API_ROOT: str = "https://app.huntbase.io/api/v1"

# HTTP behaviour
REQUEST_TIMEOUT_SECONDS: int = 30
MAX_RETRIES: int = 3
RETRY_BACKOFF_SECONDS: int = 2
MAX_RETRY_AFTER_SECONDS: int = 30
RATE_LIMIT_STATUS_CODE: int = 429
# GET requests (and idempotent POSTs) retry on these; other POSTs only on 429.
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({RATE_LIMIT_STATUS_CODE, 500, 502, 503, 504})
# Read-only or idempotent POST routes that may be retried like GET requests.
IDEMPOTENT_POST_ENDPOINTS: frozenset[str] = frozenset({"intel_lookup", "watchlist_values"})
# POST routes that create something: sent once per call with an Idempotency-Key.
IDEMPOTENCY_KEY_ENDPOINTS: frozenset[str] = frozenset({"start_hunt", "scout_jobs"})
IDEMPOTENCY_KEY_HEADER: str = "Idempotency-Key"
# API Root hosts that must never receive the API key.
BLOCKED_API_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1", "169.254.169.254"})
LINK_LOCAL_PREFIX: str = "169.254."

# Huntbase REST routes, relative to the API Root (".../api/v1").
# Kept in one place so they can follow the backend contract.
ENDPOINTS: dict[str, str] = {
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
APP_PATHS: dict[str, str] = {
    "hunt": "/hunts/{hunt_id}",
    "finding": "/findings/{finding_id}",
    "insight": "/insights/{insight_id}",
    "entity": "/entities/{entity_id}",
    "indicator": "/intelligence/indicators/{indicator_id}",
    "approvals": "/needs-you?lane=approvals",
    "approval": "/needs-you?lane=approvals&proposal={proposal_id}",
}
LINK_SOURCE: str = "google_secops"

# Enrichment
ENRICHMENT_PREFIX: str = "HB"
INTEL_LOOKUP_BATCH_SIZE: int = 100
ENTITY_SEARCH_LIMIT: int = 5
DEFAULT_SUSPICIOUS_THRESHOLD: int = 70


# Hunts
HUNT_SESSION_MODES: tuple[str, ...] = ("guided", "supervised", "autonomous")
MAX_HUNT_SEED_VALUES: int = 20
SCOUT_INITIATIVES: tuple[str, ...] = ("low", "medium")
MAX_SCOUT_QUESTION_CHARS: int = 4000
EXTERNAL_REF_SOURCE: str = "google_secops"
DEFAULT_HUNT_SESSION_MODE: str = "supervised"
HUNT_TERMINAL_STATUSES: frozenset[str] = frozenset({"closed", "concluded", "completed", "resolved", "archived"})

# Approvals
DEFAULT_PENDING_APPROVALS_LIMIT: int = 20
MAX_PENDING_APPROVALS_LIMIT: int = 100

# Scout
SCOUT_TERMINAL_OK: frozenset[str] = frozenset({"succeeded", "completed", "done"})
SCOUT_TERMINAL_FAILED: frozenset[str] = frozenset({"failed", "error", "cancelled", "canceled", "expired", "lost"})

# Connector
DEFAULT_MAX_ALERTS_PER_CYCLE: int = 50
DEFAULT_MAX_HOURS_BACKWARDS: int = 24
CONNECTOR_PAGE_SIZE: int = 50
CONNECTOR_TEST_RUN_MAX_ALERTS: int = 5
WATERMARK_KEY: str = "huntbase_watermarks"
PROCESSED_IDS_KEY: str = "huntbase_processed_ids"
MAX_STORED_IDS: int = 2000
SOURCE_FINDINGS: str = "Findings"
SOURCE_INSIGHTS: str = "Insights"
SOURCE_BOTH: str = "Findings and Insights"
DEFAULT_FINDING_DISPOSITIONS: tuple[str, ...] = ("confirmed",)
DEFAULT_INSIGHT_MIN_SEVERITY: str = "high"
# GET /insights filters on event time, not ingest time: re-read this far behind the watermark
INSIGHT_OVERLAP_MINUTES: int = 60
DEVICE_PRODUCT: str = "Huntbase"
DEVICE_VENDOR: str = "Huntbase"
RULE_GENERATOR_FINDING: str = "Huntbase Finding"
RULE_GENERATOR_INSIGHT: str = "Huntbase Insight"

# SOAR alert priority values
PRIORITY_INFO: int = -1
PRIORITY_LOW: int = 40
PRIORITY_MEDIUM: int = 60
PRIORITY_HIGH: int = 80
PRIORITY_CRITICAL: int = 100
SEVERITY_TO_PRIORITY: dict[str, int] = {
    "informational": PRIORITY_INFO,
    "info": PRIORITY_INFO,
    "unknown": PRIORITY_INFO,
    "low": PRIORITY_LOW,
    "medium": PRIORITY_MEDIUM,
    "high": PRIORITY_HIGH,
    "critical": PRIORITY_CRITICAL,
    "fatal": PRIORITY_CRITICAL,
}
SEVERITY_ORDER: tuple[str, ...] = ("informational", "low", "medium", "high", "critical")

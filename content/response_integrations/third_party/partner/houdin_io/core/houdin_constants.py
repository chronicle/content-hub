from __future__ import annotations

INTEGRATION_NAME: str = "Houdin-io"
INTEGRATION_VERSION: str = "5.0"
API_ROOT: str = "https://app.houdin.io/api/v1"
APP_ROOT: str = "https://app.houdin.io"
USER_AGENT: str = f"{INTEGRATION_NAME}-SecOps/{INTEGRATION_VERSION}"

PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
SCAN_ARTIFACT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Scan Artifact"
ENRICH_ENTITIES_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Enrich Entities"

# Seconds before one HTTP call to Houdin is given up.
REQUEST_TIMEOUT: int = 30
# A 5xx or a dropped connection is retried this many times before failing.
MAX_RETRIES: int = 2
# POST /scan/result accepts up to this many scan IDs per call.
RESULT_BATCH_SIZE: int = 50

# Prefix of every enrichment field written on an entity.
ENRICHMENT_PREFIX: str = "Houdin-io"

# The MesmerAI modules: the verdict (score, confidence, summary, tags, related
# indicators) and the human summary. The API adds both when the scanner list is
# omitted; an explicit list must name them, so normalize_scanners appends them.
MESMER_MODULES: tuple[str, ...] = ("mesmer", "mesmer-summary")

# Scanner shortnames the API accepts. Public and Pro sources first, then the
# Enterprise hunting connectors, which only run once configured on the account.
SCANNERS: tuple[str, ...] = (
    "vt",
    "urlscan",
    "abuseipdb",
    "alienvault",
    "triage",
    "threatfox",
    "urlhaus",
    "gtithreatactors",
    "misp",
    "netlas",
    "rosti",
    "mesmerdeepsearch",
    "mesmerunmask",
    "servicenow",
    "jira",
    "elasticsearch",
    "sentinel",
    "mde",
    "crowdstrike",
    "googlesecops",
)

# Score at or above which an entity is flagged suspicious, unless the action
# parameter says otherwise.
DEFAULT_SUSPICIOUS_THRESHOLD: int = 7

SCAN_STATUS_DONE: str = "Done"
SCAN_STATUS_IN_PROGRESS: str = "In progress"

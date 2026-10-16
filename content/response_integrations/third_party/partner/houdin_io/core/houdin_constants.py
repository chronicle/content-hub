from __future__ import annotations

INTEGRATION_NAME = "Houdin-io"
INTEGRATION_VERSION = "5.0"
API_ROOT = "https://app.houdin.io/api/v1"
APP_ROOT = "https://app.houdin.io"
USER_AGENT = f"{INTEGRATION_NAME}-SecOps/{INTEGRATION_VERSION}"

PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
SCAN_ARTIFACT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Scan Artifact"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"

# Seconds before one HTTP call to Houdin is given up.
REQUEST_TIMEOUT = 30
# A 5xx or a dropped connection is retried this many times before failing.
MAX_RETRIES = 2
# POST /scan/result accepts up to this many scan IDs per call.
RESULT_BATCH_SIZE = 50
# Each run of an asynchronous action waits this long for the scans before handing
# back to the platform: most sources answer in seconds and a cached scan at once,
# so the usual case completes in one run instead of waiting for the platform's
# polling interval (an hour by default). Only URLScan (one to two minutes) and
# AlienVault on a slow day go through the asynchronous cycle.
RUN_WAIT_SECONDS = 24
RUN_POLL_INTERVAL = 3

# Prefix of every enrichment field written on an entity.
ENRICHMENT_PREFIX = "Houdin-io"

# The MesmerAI modules: the verdict (score, confidence, summary, tags, related
# indicators) and the human summary. The API adds both when the scanner list is
# omitted; an explicit list must name them, so the manager appends them.
MESMER_MODULES = ("mesmer", "mesmer-summary")

# Scanner shortnames the API accepts. Public and Pro sources first, then the
# Enterprise hunting connectors, which only run once configured on the account.
SCANNERS = (
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
DEFAULT_SUSPICIOUS_THRESHOLD = 7

SCAN_STATUS_DONE = "Done"
SCAN_STATUS_IN_PROGRESS = "In progress"

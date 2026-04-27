from __future__ import annotations
INTEGRATION_NAME = "Sumo Logic"
INTEGRATION_IDENTIFIER = "Sumologic"

# Action Script Names
PING_SCRIPT_NAME = "Ping"
SEARCH_SCRIPT_NAME = "Search"

ENDPOINTS = {
    "search_job": "api/v1/search/jobs",
    "delete_job": "api/v1/search/jobs/{job_id}",
    "get_job_info": "api/v1/search/jobs/{job_id}",
    "get_search_results": "api/v1/search/jobs/{job_id}/messages",
}

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

ERROR_STATUSES = ["FORCE PAUSED", "CANCELED"]
COMPLETED_STATUS = "DONE GATHERING RESULTS"
LIMIT_PER_REQUEST = 100

DEFAULT_MAX_SEARCH_JOB_RESULTS = 25

SEARCH_JOB_AWAIT_INTERVAL_SECONDS = 1
DEFAULT_SINCE_TIME_DAYS = 30

DEFAULT_MAX_ALERTS = 25

CONNECTOR_NAME = "Sumologic Connector"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
TIMEOUT_THRESHOLD = 0.9

UNIX_FORMAT = 1
DATETIME_FORMAT = 2
DEFAULT_DAYS_BACKWARDS = 3
QUERY = "_index={}"
DEFAULT_VENDOR = "Sumologic"
DEFAULT_PRODUCT = "Sumologic"
SUMO_TIME_FIELD = "_receipttime"

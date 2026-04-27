from __future__ import annotations
INTEGRATION_NAME = "TrendVisionOne"
INTEGRATION_DISPLAY_NAME = "Trend Vision One"
INTEGRATION_PREFIX = "TREND_VISION_ONE"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
ISOLATE_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Isolate Endpoint"
EXECUTE_CUSTOM_SCRIPT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute Custom Script"
UNISOLATE_ENDPOINT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Unisolate Endpoint"
UPDATE_WORKBENCH_ALERT_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Update Workbench Alert"
)
SUBMIT_FILE_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Submit File"
SUBMIT_URL_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Submit URL"
EXECUTE_EMAIL_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Execute Email"

ENDPOINTS = {
    "healthcheck": "/v3.0/healthcheck/connectivity",
    "get_alerts": "/v3.0/workbench/alerts",
    "alert_details": "/v3.0/workbench/alerts/{alert_id}",
    "search_endpoint": "/v3.0/eiqs/endpoints",
    "isolate_endpoint": "/v3.0/response/endpoints/isolate",
    "unisolate_endpoint": "/v3.0/response/endpoints/restore",
    "get_task": "/v3.0/response/tasks/{task_id}",
    "get_scripts": "/v3.0/response/customScripts",
    "run_script": "/v3.0/response/endpoints/runScript",
    "submit_file": "/v3.0/sandbox/files/analyze",
    "submit_url": "/v3.0/sandbox/urls/analyze",
    "execute_email": "/v3.0/response/emails/{email_action}",
    "get_task_detail": "/v3.0/sandbox/tasks/{task_id}",
    "get_email_task_detail": "/v3.0/response/tasks/{task_id}",
    "get_task_result": "/v3.0/sandbox/analysisResults/{task_id}",
}

ENRICHMENT_PREFIX = "TrendVisionOne"
SUCCESS_STATUS = "succeeded"
FAILED_STATUS = "failed"
REJECTED_STATUS = "rejected"
RUNNING_STATUS = "running"
RATE_LIMIT_EXCEEDED = "Rate limit exceeded"
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
DEFAULT_TIMEOUT = 300
SUCCESSFUL_STATUS_CODES = [200, 201, 202, 203, 204, 205, 206, 207, 208, 226]
PAYLOAD_CHUNK_SIZE = 10
TOO_MANY_REQUESTS = 429

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Workbench Alerts Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 10
DEFAULT_MAX_LIMIT = 100
DEVICE_VENDOR = "Trend Vision One"
DEVICE_PRODUCT = "Trend Vision One"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
POSSIBLE_SEVERITIES = ["low", "medium", "high", "critical"]
SEVERITY_MAPPING = {"INFO": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}

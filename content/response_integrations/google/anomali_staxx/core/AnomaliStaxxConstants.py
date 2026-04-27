from __future__ import annotations
PROVIDER_NAME = "Anomali Staxx"
DEVICE_VENDOR = "Anomali"
DEVICE_PRODUCT = "Anomali Staxx"
ALERTS_LIMIT = 50
INDICATORS_FETCH_SIZE = 5000
QUERY_TYPE = "json"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S %p"
REQUEST_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Do not change the order, It's used in Manager._get_severities_from
SEVERITIES = ["low", "medium", "high", "very-high"]
VERY_HIGH_SEVERITY = "very-high"
CRITICAL_SEVERITY = "critical"
DEFAULT_SEVERITY = "Medium"

# CONNECTORS
INDICATORS_CONNECTOR_NAME = f"{PROVIDER_NAME} - Indicators Connector"
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
DEFAULT_TIME_FRAME = 1

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"

# SIEM
ANOMALI_STAXX_TO_SIEM_SEVERITY = {"low": 40, "medium": 60, "high": 80, "very-high": 100}

ENDPOINTS = {"login": "/api/v1/login", "intelligence": "/api/v1/intelligence"}

HEADERS = {"Content-Type": "application/json"}

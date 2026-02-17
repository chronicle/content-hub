from __future__ import annotations

USER_AGENT = "google-secops-soar-v1.0.0"

INTEGRATION_NAME = "GreyNoise"

RESULT_VALUE_TRUE = True
RESULT_VALUE_FALSE = False
COMMON_ACTION_ERROR_MESSAGE = "Error while executing action {}. Reason: {}"

# Scripts Name
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
QUICK_IP_LOOKUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Quick IP Lookup"
GET_CVE_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get CVE Details"
EXECUTE_GNQL_QUERY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute GNQL Query"
IP_TIMELINE_LOOKUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - IP Timeline Lookup"
IP_LOOKUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - IP Lookup"


# Error Messages
NO_CVE_ENTITIES_ERROR = "No CVE type entities found to process."
INVALID_CVE_FORMAT_ERROR = "Invalid CVE format for {}. Expected format: CVE-YYYY-NNNN"
NO_IP_ENTITIES_ERROR = "No IP ADDRESS entities found to process."
NO_TIMELINE_DATA_ERROR = "No timeline data found for IP: {}"
IP_NOT_FOUND_ERROR = "IP {} not found in GreyNoise dataset."
COMMUNITY_TIER_MESSAGE = "Using Community API tier - limited data available."

# GNQL Query Constants
GNQL_PAGE_SIZE = 1000
MAX_RESULT_SIZE = 1000

# Connector Constants
GNQL_CONNECTOR_NAME = f"{INTEGRATION_NAME} - GNQL Connector"
MAX_CONNECTOR_RESULTS = 100
TEST_MODE_MAX_RESULTS = 10
EVENT_TYPE = "GreyNoise Indicator Alert"

# Severity Mapping
SEVERITY_MAP = {"low": 40, "medium": 60, "high": 80, "critical": 100}

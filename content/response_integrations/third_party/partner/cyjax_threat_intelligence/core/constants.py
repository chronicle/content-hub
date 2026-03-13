from __future__ import annotations

INTEGRATION_NAME = "Cyjax"

RESULT_VALUE_TRUE = True
RESULT_VALUE_FALSE = False
COMMON_ACTION_ERROR_MESSAGE = "Error while executing action {}. Reason: {}"
NO_ENTITIES_ERROR = "No entities found to process."

# Signature and timeout settings
DEFAULT_REQUEST_TIMEOUT = 60
RETRY_COUNT = 2
FIRST_RETRY_DELAY = 15  # seconds
SECOND_RETRY_DELAY = 30  # seconds

# Scripts Name
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ENRICH_IOCS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich IOCs"
DOMAIN_MONITOR_SCRIPT_NAME = f"{INTEGRATION_NAME} - Domain Monitor"
LIST_DATA_BREACHES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Data Breaches"

# API Endpoints
CYJAX_API_BASE_URL = "https://api.cymon.co/{api_version}"
PING_ENDPOINT = "/indicator-of-compromise"
ENRICH_IOC_ENDPOINT = "/indicator-of-compromise/enrichment"
DOMAIN_MONITOR_ENDPOINT = "/domain-monitor/potential-malicious-domain"
LIST_DATA_BREACH_ENDPOINT = "/data-leak/credentials"

# API Version
CYJAX_API_VERSION = "v2"

# Default values
DEFAULT_PAGE_NUMBER = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_RECORDS_LIMIT = 1000

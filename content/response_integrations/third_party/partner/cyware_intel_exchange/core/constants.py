from __future__ import annotations

INTEGRATION_NAME = "CywareIntelExchange"
USER_AGENT_NAME = "cyware/intel-exchange (GoogleSecopsSOAR/1.0.0)"

RESULT_VALUE_TRUE = True
RESULT_VALUE_FALSE = False
COMMON_ACTION_ERROR_MESSAGE = "Error while executing action {}. Reason: {}"
NO_ENTITIES_ERROR = "No entities found to process."
NO_VALID_IOC_ERROR = "None of the provided indicators were found in Cyware Intel Exchange"

SIGNATURE_EXPIRY_SECONDS = 25
DEFAULT_REQUEST_TIMEOUT = 60
RETRY_COUNT = 3
WAIT_TIME_FOR_RETRY = 60

# Scripts Name
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
CREATE_INTEL_IN_CTIX_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Intel in CTIX"
GET_ALLOWED_IOCS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Allowed IOCs"
ADD_ALLOWED_IOCS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add IOCs to Allowlist"
REMOVE_ALLOWED_IOCS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove IOCs from Allowlist"
GET_IOC_DETAILS_BY_ENRICHING_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get IOC Details"
ADD_TAGS_TO_IOC_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Tags to IOC"
REMOVE_TAGS_FROM_IOC_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Tags from IOC"
ADD_NOTE_TO_IOC_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Note to IOCs"
MARK_INDICATOR_FALSE_POSITIVE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Mark IOCs False Positive"

# API Endpoints
PING_ENDPOINT = "/ping/"
CREATE_INTEL_ENDPOINT = "/conversion/quick-intel/create-stix/"
QUICK_INTEL_STATUS_ENDPOINT = "/conversion/quick-intel/receive-report/"
ALLOWED_INDICATORS_ENDPOINT = "/conversion/allowed_indicators/"
BULK_LOOKUP_ENDPOINT = "/ingestion/openapi/bulk-lookup/{object_type}/"
BULK_ACTION_ADD_TAG_ENDPOINT = "/ingestion/threat-data/bulk-action/add_tag/"
BULK_ACTION_REMOVE_TAG_ENDPOINT = "/ingestion/threat-data/bulk-action/remove_tag/"
BULK_ACTION_UNWHITELIST_ENDPOINT = "/ingestion/threat-data/bulk-action/un_whitelist/"
BULK_ACTION_FALSE_POSITIVE_ENDPOINT = "/ingestion/threat-data/bulk-action/false_positive/"
ADD_NOTE_ENDPOINT = "/ingestion/notes/"
TAGS_ENDPOINT = "/ingestion/tags/"

# Default values
DEFAULT_PAGE_SIZE = 1000
DEFAULT_PAGE_NUMBER = 1
MAX_PAGE_SIZE = 1000
TAGS_PAGE_SIZE = 2000
DEFAULT_BULK_LOOKUP_FIELDS = "id,name"
QUICK_INTEL_STATUS_POLL_INTERVAL = 5
QUICK_INTEL_STATUS_MAX_ATTEMPTS = 24
QUICK_INTEL_STATUS_SUCCESS_STATUSES = {"CREATED", "SUCCESS"}
QUICK_INTEL_STATUS_FAILURE_STATUSES = {"FAILED", "ERROR"}

# Table display limits
MAX_TABLE_RECORDS = 10

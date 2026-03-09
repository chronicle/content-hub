from __future__ import annotations

INTEGRATION_NAME = "Censys"

INTEGRATION_VERSION = "1.0.0"

# API Configuration
API_ROOT = "https://api.platform.censys.io"

RESULT_VALUE_TRUE = True
RESULT_VALUE_FALSE = False
DEFAULT_DEVICE_VENDOR = "Censys"
DEFAULT_DEVICE_PRODUCT = INTEGRATION_NAME
RULE_GENERATOR = DEFAULT_DEVICE_VENDOR
COMMON_ACTION_ERROR_MESSAGE = "Error while executing action {}. Reason: {}"
INVALID_AND_COUNT_CONDITIONS_FORMAT = (
    "Invalid format in And Count Conditions: '{}'. Expected format: field:value"
)
INVALID_FIELD_VALUE_PAIR = "Invalid field-value pair: '{}'. Both field and value must be non-empty"
EMPTY_AND_COUNT_CONDITIONS = "And Count Conditions parameter cannot be empty"
NO_VALID_CONDITIONS_FOUND = "No valid conditions found in And Count Conditions parameter"
THREAT_HUNTING_ACCESS_REQUIRED = "This action requires active access to the Threat Hunting Module"
DEFAULT_PAGE_SIZE = 1000
RETRY_COUNT = 3
WAIT_TIME_FOR_RETRY = 5
DEFAULT_RESULTS_LIMIT = 10000000
RATE_LIMIT_EXCEEDED_STATUS_CODE = 429
UNAUTHORIZED_STATUS_CODE = 401
VALIDATION_ERROR_STATUS_CODES = [400, 422]
DEFAULT_REQUEST_TIMEOUT = 60
DEFAULT_OFFSET = "0"
DEFAULT_LIMIT = "100"
MAX_TABLE_RECORDS = 1000
MAX_JSON_CHARS = 300
MAX_INT_VALUE = 65535
INTERNAL_SERVER_ERROR_STATUS_CODES = [500, 502, 503, 504]
MAX_RECORD_THRESHOLD = 1000
MAX_PAGINATION_CALLS = 10
SEARCH_PAGE_SIZE = 100
MAX_PAYLOAD_SIZE_BYTES = 24 * 1024 * 1024  # 24 MB

# Default Values
DEFAULT_VALUE_NA = "N/A"

# Censys Platform URLs
CENSYS_PLATFORM_BASE_URL = "https://platform.censys.io"
CENSYS_HOSTS_URL_TEMPLATE = (
    "{base_url}/hosts/{host_id}?at_time={encoded_time}&org={organization_id}"
)

# Resource Types for Host History
RESOURCE_TYPE_SERVICE_SCANNED = "service_scanned"
RESOURCE_TYPE_REVERSE_DNS_RESOLVED = "reverse_dns_resolved"
RESOURCE_TYPE_ENDPOINT_SCANNED = "endpoint_scanned"
RESOURCE_TYPE_FORWARD_DNS_RESOLVED = "forward_dns_resolved"
RESOURCE_TYPE_JARM_SCANNED = "jarm_scanned"
RESOURCE_TYPE_LOCATION_UPDATED = "location_updated"
RESOURCE_TYPE_ROUTE_UPDATED = "route_updated"
RESOURCE_TYPE_WHOIS_UPDATED = "whois_updated"

# Scripts Name
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
INITIATE_RESCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Initiate Rescan"
GET_RESCAN_STATUS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Rescan Status"
GET_HOST_HISTORY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Host History"
# GET_RELATED_INFRASTRUCTURE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Related Infrastructure"
ENRICH_IPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich IPs"
ENRICH_WEB_PROPERTIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Web Properties"
ENRICH_CERTIFICATES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Certificates"

# Action Identifiers
PING_ACTION_IDENTIFIER = "ping"
INITIATE_RESCAN_ACTION_IDENTIFIER = "initiate_rescan"
GET_RESCAN_STATUS_ACTION_IDENTIFIER = "get_rescan_status"
GET_HOST_HISTORY_ACTION_IDENTIFIER = "get_host_history"
# GET_RELATED_INFRASTRUCTURE_SEARCH_QUERY_IDENTIFIER = "get_related_infrastructure_search_query"
ENRICH_IPS_ACTION_IDENTIFIER = "enrich_ips"
ENRICH_WEB_PROPERTIES_ACTION_IDENTIFIER = "enrich_web_properties"
ENRICH_CERTIFICATES_ACTION_IDENTIFIER = "enrich_certificates"

# Error Messages
NO_ADDRESS_ENTITIES_ERROR = "No ADDRESS type entities found in scope."
NO_WEB_ENTITIES_ERROR = "No ADDRESS or HOSTNAME type entities found in scope."
NO_FILEHASH_ENTITIES_ERROR = "No FILEHASH type entities found in the current scope."
INVALID_IP_FORMAT_ERROR = "Invalid IP address format: {}"
INVALID_PORT_FORMAT_ERROR = "Invalid port value: {}"
DEFAULT_PORTS = "80,443"

# API Services and Versions
API_VERSION_V3 = "/v3"

# API Endpoints
ENDPOINTS = {
    PING_ACTION_IDENTIFIER: (API_VERSION_V3 + "/accounts/organizations/{organization_id}"),
    INITIATE_RESCAN_ACTION_IDENTIFIER: API_VERSION_V3 + "/global/scans/rescan",
    GET_RESCAN_STATUS_ACTION_IDENTIFIER: API_VERSION_V3 + "/global/scans/{scan_id}",
    GET_HOST_HISTORY_ACTION_IDENTIFIER: API_VERSION_V3 + "/global/asset/host/{host_id}/timeline",
    # GET_RELATED_INFRASTRUCTURE_SEARCH_QUERY_IDENTIFIER: API_VERSION_V3 + "/global/search/query",
    ENRICH_IPS_ACTION_IDENTIFIER: API_VERSION_V3 + "/global/asset/host",
    ENRICH_WEB_PROPERTIES_ACTION_IDENTIFIER: (API_VERSION_V3 + "/global/asset/webproperty"),
    ENRICH_CERTIFICATES_ACTION_IDENTIFIER: (API_VERSION_V3 + "/global/asset/certificate"),
}

# IOC Types for Initiate Rescan
IOC_TYPE_SERVICE_ID = "Service"
IOC_TYPE_WEB_ORIGIN = "Web Origin"

# Transport Protocols
TRANSPORT_PROTOCOL_UNKNOWN = "Unknown"
TRANSPORT_PROTOCOL_TCP = "TCP"
TRANSPORT_PROTOCOL_UDP = "UDP"
TRANSPORT_PROTOCOL_ICMP = "ICMP"
TRANSPORT_PROTOCOL_QUIC = "QUIC"

# Enrichment Prefixes
ENRICHMENT_PREFIX = "Censys_"
ENRICHMENT_PREFIX_CERT = f"{ENRICHMENT_PREFIX}cert_"
ENRICHMENT_PREFIX_WEB = ENRICHMENT_PREFIX

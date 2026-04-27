from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes

INTEGRATION_IDENTIFIER = "TrendMicroApexCentral"
INTEGRATION_DISPLAY_NAME = "Trend Micro Apex Central"

# Authentication
CHECKSUM_ALGORITHM = "HS256"
JWT_TOKEN_VERSION = "V1"

# Actions script names
PING_ACTION_SCRIPT_NAME = "Ping"
CREATE_ENTITY_UDSO_SCRIPT_NAME = "Create Entity UDSO"
CREATE_FILE_UDSO_SCRIPT_NAME = "Create File UDSO"
ENRICH_ENTITIES_SCRIPT_NAME = "Enrich Entities"
ISOLATE_ENDPOINTS_SCRIPT_NAME = "Isolate Endpoints"
UNISOLATE_ENDPOINTS_SCRIPT_NAME = "Unisolate Endpoints"

# API
AUTHORIZATION_ERROR_STATUS_CODE = 401

DEFAULT_SCAN_ACTION = "Block"
SHA1_HASH_LENGTH = 40

ENTITY_TYPE_TO_UDSO_TYPE = {
    EntityTypes.ADDRESS: "ip",
    EntityTypes.URL: "url",
    EntityTypes.FILEHASH: "file_sha1",
}
UDSO_FILE_TYPE = "file"
UDSO_DOMAIN_TYPE = "domain"
ISOLATION_STATUS_UNKNOWN = "N/A"
ISOLATION_STATUS_NOT_SUPPORTED = "not_supported"
ISOLATION_STATUS_NORMAL = "normal"
ISOLATION_STATUS_ISOLATED = "isolated"
ISOLATION_STATUS_PENDING = "endpoint_isolation_pending"
UNISOLATION_STATUS_PENDING = "connection_restoration_pending"
ISOLATION_STATUSES = {
    0: ISOLATION_STATUS_UNKNOWN,
    1: ISOLATION_STATUS_NORMAL,
    2: ISOLATION_STATUS_ISOLATED,
    3: ISOLATION_STATUS_PENDING,
    4: UNISOLATION_STATUS_PENDING,
}
ENRICHMENT_PREFIX = "TMAC"
DEFAULT_LIMIT = 20
ENDPOINT_SENSOR_TASK_TYPE = 4
SUPPORTED_UDSO_ENTITY_TYPES = [
    EntityTypes.URL,
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
]
SUPPORTED_ENDPOINTS_ENTITY_TYPES_LOWERED = [
    EntityTypes.HOSTNAME.lower(),
    EntityTypes.MACADDRESS.lower(),
    EntityTypes.ADDRESS.lower(),
]
FOUND_UDSO_CSV_TABLE_TITLE = "Found UDSO"
FOUND_ENDPOINTS_CSV_TABLE_TITLE = "Found Endpoints"
NOT_ASSIGNED = "N/A"
UDSO_GENERAL_INSIGHT_TITLE = "User-Defined Suspicious Objects Information"
ENDPOINTS_GENERAL_INSIGHT_TITLE = "Endpoint Information"

ENDPOINTS_INSIGHT_TEMPLATE = """
<p style="margin-bottom: -10px;font-size:15px"><strong>Endpoint: {endpoint_identifier}</strong></p>
<b>IP Address:</b> {ip_address}
<b>Mac Address:</b> {mac_address}
<b>Hostname:</b> {host_name}
<b>Isolation Status:</b> {isolation_status}
<b>AD Domain:</b> {ad_domain}
<b>Endpoint Sensor:</b> {has_endpoint_sensor}
"""

UDSO_INSIGHT_TEMPLATE = """
<p style="margin-bottom: -10px;font-size:15px"><strong>Entity: {entity_identifier}</strong></p>
<b>Action:</b> {scan_action}
<b>Notes:</b> {notes}
"""

ASYNC_ACTION_TIMEOUT_THRESHOLD_MS = 35000
MAX_UDSO_NOTES_CHARACTERS_LENGTH = 256

from __future__ import annotations
PROVIDER_NAME = "SolarWinds Orion"

# ACTIONS
PING_SCRIPT_NAME = f"{PROVIDER_NAME} - Ping"
EXECUTE_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Execute Query"
EXECUTE_ENTITY_QUERY_SCRIPT_NAME = f"{PROVIDER_NAME} - Execute Entity Query"
ENRICH_ENDPOINT_SCRIPT_NAME = f"{PROVIDER_NAME} - EnrichEndpoint"

ENDPOINTS = {"test_connectivity": "/SolarWinds/InformationService/v3/Json/Query"}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

DEFAULT_RESULTS_LIMIT = 100
BAD_REQUEST_STATUS_CODE = 400
DEFAULT_IP_KEY = "IpAddress"
DEFAULT_HOSTNAME_KEY = "Hostname"
DEFAULT_DISPLAY_NAME_KEY = "DisplayName"
ENRICHMENT_PREFIX = "SLRW_ORION"
ENRICHMENT_QUERY = (
    "SELECT IpAddress, DisplayName, NodeDescription, ObjectSubType,Description,SysName, Caption,DNS,"
    "Contact,Status,StatusDescription,IOSImage,IOSVersion,GroupStatus,LastBoot,SystemUpTime,"
    "AvgResponseTime,CPULoad,PercentMemoryUsed,MemoryAvailable,Severity,Category,EntityType, IsServer, "
    "IsOrionServer FROM Orion.Nodes "
)

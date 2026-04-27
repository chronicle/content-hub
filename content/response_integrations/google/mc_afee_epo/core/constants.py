from __future__ import annotations
from enum import Enum
from .McafeeQueryBuilder import QueryOperatorEnum

INTEGRATION_NAME = "McAfeeEPO"
PRODUCT_NAME = "McAfee ePO"
DEVICE_VENDOR = "McAfee"

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ADD_TAG_SCRIPT_NAME = f"{INTEGRATION_NAME} - AddTag"
REMOVE_TAG_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remove Tag"
GET_AGENT_INFORMATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Agent Information"
GET_HOSTS_IPS_STATUS_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetHostIPSStatus"
GET_LAST_COMMUNICATION_TIME_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - GetLastCommunicationTIme"
)
GET_MCAFEE_EPO_AGENT_VERSION_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - GetMcAfeeEpoAgentVersion"
)
GET_HOST_NETWORK_IPS_STATUS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - GetHostNetworkIPSStatus"
)
GET_DAT_VERSION_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetDatVersion"
UPDATE_MCAFEE_AGENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - UpdateMcafeeAgent"
RUN_FULL_SCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - RunFullScan"
GET_SYSTEM_INFORMATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetSystemInformation"
GET_VIRUS_ENGINE_AGENT_VERSION_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - GetVirusEngineAgentVersion"
)
GET_EVENTS_FOR_HASH_SCRIPT_NAME = f"{INTEGRATION_NAME} - GetEventsForHash"
COMPARE_SERVER_AND_AGENT_DAT_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - CompareServerAndAgentDAT"
)
EXECUTE_CUSTOM_QUERY_SCRIPT_NAME = f"{INTEGRATION_NAME} - ExecuteCustomQuery"
EXECUTE_ENTITY_QUERY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute Entity Query"
LIST_TASKS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Tasks"
EXECUTE_QUERY_BY_ID_SCRIPT_NAME = f"{INTEGRATION_NAME} - Execute Query By ID"
LIST_QUERIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Queries"
GET_ENDPOINT_EVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Endpoint Events"

# Connectors
THREATS_CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_NAME} - Threats Connector"

# TABLES NAMES
HOST_IPS_STATUS_TABLE_NAME = "Hosts IPS Statuses"
HOST_NETWORK_IPS_STATUS_TABLE_NAME = "Hosts Network IPS Statuses"
GET_LAST_COMMUNICATION_TIME_TABLE_NAME = "Last Communication Times"
UPDATE_MCAFEE_AGENT_TABLE_NAME = "Update Agents Results"
SYSTEM_INFORMATION_TABLE_NAME = f"{PRODUCT_NAME}: Endpoints"
CUSTOM_QUERY_TABLE_NAME = "McAfee Query Results"
QUERY_RESULTS_TABLE_NAME = "Query Results"
LIST_QUERIES_TABLE_NAME = "Available Queries"
QUERY_DATA_TABLE_NAME = "McAfee Query Results"
LIST_TASKS_TABLE_NAME = "Available Queries"
ENDPOINT_EVENTS_ENTITY_TABLE_NAME = "Name: {}"

# INSIGHTS NAMES
EVENTS_FOR_HASH_INSIGHT_NAME = "Found events at McAfee EPO for current hash"
SYSTEM_INFORMATION_INSIGHT_NAME = "General Insight"


# Enums
class SortOrderEnum(Enum):
    ASC = "ASC"
    DESC = "DESC"


class TimeFrameEnum(Enum):
    LAST_HOUR = "Last Hour"
    LAST_6_HOURS = "Last 6 Hours"
    LAST_24_HOURS = "Last 24 Hours"
    LAST_WEEK = "Last Week"
    LAST_MONTH = "Last Month"
    CUSTOM = "Custom"


class FilterStrategy(Enum):
    Equal = "Equal"
    Contains = "Contains"


FILTER_STRATEGY_MAPPING = {
    FilterStrategy.Equal.value: lambda item, value: str(item).lower()
    == str(value).lower(),
    FilterStrategy.Contains.value: lambda item, value: str(value).lower()
    in str(item).lower(),
}

CROSS_ENTITY_OPERATOR_MAPPING = {
    operator.name: operator.value for operator in QueryOperatorEnum
}

# MAPPINGS
TIME_FRAME_MAPPING = {
    TimeFrameEnum.LAST_HOUR.value: 3600000,
    TimeFrameEnum.LAST_6_HOURS.value: 21600000,
    TimeFrameEnum.LAST_24_HOURS.value: 86400000,
    TimeFrameEnum.LAST_WEEK.value: 604800000,
    TimeFrameEnum.LAST_MONTH.value: 2592000000,
}


# PREFIXES
MCAFEE_EPO_PROVIDER_PREFIX = "EPO_"
MCAFEE_ePO_PROVIDER_PREFIX = "ePO"


# REGEXPS
VALID_EMAIL_REGEXP = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


# CONNECTOR CONSTANTS
STORED_IDS_LIMIT = 1000


SEVERITY_TO_PRIORITY_MAPPING = {
    "INFO": -1,
    "LOW": 40,
    "MEDIUM": 60,
    "HIGH": 80,
    "CRITICAL": 100,
}

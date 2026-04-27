from __future__ import annotations
INTEGRATION_NAME = "McAfeeESM"
INTEGRATION_DISPLAY_NAME = "McAfeeESM"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
SEND_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Send Query To ESM"
SEND_ENTITY_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Send Entity Query To ESM"
GET_SIMILAR_EVENTS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Similar Events"
ADD_VALUES_TO_WATCHLIST_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add Values To Watchlist"
)
REMOVE_VALUES_FROM_WATCHLIST_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Remove Values From Watchlist"
)

ENDPOINTS = {
    "ping": "/rs/esm/v2/alarmGetTriggeredAlarms?triggeredTimeRange=CUSTOM&customStart=2023-01-04T20:55:00Z&customEnd"
    "=2023-01-05T23:00:00Z&pageSize=1&pageNumber=1",
    "get_alarms": "/rs/esm/v2/alarmGetTriggeredAlarms",
    "get_alarm_details": "/rs/esm/v2/notifyGetTriggeredNotificationDetail",
    "get_event_details": "/rs/esm/v2/ipsGetAlertData",
    "query_status": "v1/runningQuery/queue/{query_id}",
    "create_advanced_query": "v1/runningQuery",
    "get_advanced_query_results": "v1/runningQuery/{query_id}?offset=0&page_size=200&reverse=false",
    "execute_query": "/rs/esm/v2/qryExecuteDetail",
    "get_query_status": "/rs/esm/v2/qryGetStatus",
    "get_query_results": "/rs/esm/v2/qryGetResults",
    "create_events_query": "/rs/v1/runningQuery",
    "get_watchlist": "/rs/esm/v2/sysGetWatchlists",
    "add_watchlist_values": "/rs/esm/v2/sysAddWatchlistValues",
    "remove_watchlist_values": "/rs/esm/v2/sysRemoveWatchlistValues",
    "check_correlations": "/rs/alerts/eventcorr",
    "get_correlated_events": "/rs/esm/qryGetCorrEventDataForID",
}

CUSTOM_TIME_FILTER = "CUSTOM"
DEFAULT_LIMIT = 50
QUERY_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
DEFAULT_TIMEOUT = 300
DEFAULT_HOURS_BACK = 1
DOT_STRING = "."
GET_EVENTS_API_TIMEOUT = 60

SORT_ORDER = {"ASC": "ASCENDING", "DESC": "DESCENDING"}

EVENT_QUERY_TYPE = "EVENT"
DEFAULT_QUERY_FIELDS = {
    "EVENT": [
        "Alert.IPSIDAlertID",
        "Alert.AvgSeverity",
        "Rule.msg",
        "Alert.EventCount",
        "Alert.SrcIP",
        "Alert.DstIP",
        "Alert.Protocol",
        "Alert.LastTime",
        "Action.Name",
    ],
    "FLOW": [
        "Connection.IPSIDConnectionID",
        "Connection.SrcIP",
        "Connection.SrcPort",
        "Connection.DstIP",
        "Connection.DstPort",
        "Connection.Reviewed",
        "Connection.Protocol",
        "Connection.LastTime",
        "Connection.Duration",
    ],
    "ASSET": [
        "Asset.AssetID",
        "Asset.HostName",
        "Asset.IPAddress",
        "Asset.MAC",
        "OS.OSName",
        "Asset.AssetRiskScore",
    ],
}

LOGIN_PAYLOAD = {
    "username": "",  # Base64
    "password": "",  # Base64
    "locale": "en_US",
    "os": "Win32",
}

LOGIN_URL = "esm/login"
CONNECTOR_TOKEN_FILE_NAME = "McAfee_ESM_Connector_Sessions_{hashed_configs}.json"
CONNECTOR_TOKEN_DB_KEY = "McAfee_ESM_Connector_Sessions_{hashed_configs}"
ACTION_TOKEN_FILE_NAME = "McAfee_ESM_Action_Sessions_{hashed_configs}.json"
ACTION_TOKEN_DB_KEY = "McAfee_ESM_Action_Sessions_{hashed_configs}"
ACTION_TOKEN_IDENTIFIER = "McAfee_ESM_Action_Sessions"
TOKEN_FULL_PATH = "{file_name}"
INTEGRATION_FOLDER_NAME = "McAfeeESM"
SUPPORTED_PRODUCT_VERSIONS = ["11.1", "11.2", "11.3", "11.4", "11.5"]

# Constants used as default method attribute values
DEFAULT_PAGE_SIZE = 100
FIRST_PAGE_INDEX = 1

# Field constants
ALARM_ID_FIELD = "id"

HEADERS = {"Content-Type": "application/json"}

# Connector
CONNECTOR_NAME = "McAfee ESM Connector"
CORRELATIONS_CONNECTOR_NAME = "McAfee ESM Correlations Connector"
FETCH_INTERVAL = 12
DEFAULT_TIME_FRAME = 1
DEFAULT_PADDING_TIME = 1
DEFAULT_FETCH_LIMIT = 20
CONNECTOR_DEFAULT_LIMIT = 100
STORED_IDS_LIMIT = 2500
STORED_CORRELATION_IDS_LIMIT = 2000
MAX_EVENTS_LIMIT = 199
DEVICE_VENDOR = "McAfee ESM"
DEVICE_PRODUCT = "McAfee ESM"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

COMPLETE_STATUS = "complete"
# =====================================
#             PAYLOADS                #
# =====================================
QUERY_TIME_EXPRESSION = "$Last,?Hour{hours_back},DV,DV"

# UI main query for fetching events for entity.
GET_EVENTS_MAIN_QUERY = {
    "query": {
        "fields": {
            "opt": "SELECT",
            "opr": [
                "Alert.IPSIDAlertID",
                "Alert.SrcIP",
                "Alert.SrcPort",
                "Alert.DstIP",
                "Alert.DstPort",
                "Alert.Protocol",
                "Alert.LastTime",
                "Action.Name",
            ],
            "exp": None,
        },
        "sources": {
            "opt": "SOURCE",
            "opr": [],
            "exp": [
                {"opt": "EQUALS", "opr": ["QUERYID", "6"], "exp": []},
                {"opt": "EQUALS", "opr": ["ESMQUERYTYPE", "EVENT"], "exp": []},
                {
                    "opt": "EQUALS",
                    "opr": ["ESMQUERYDEVICESOURCE", "Alert.IPSID"],
                    "exp": [],
                },
            ],
        },
        "filters": {
            "opt": "AND",
            "opr": None,
            "exp": [
                {
                    "opt": "EQUALS",
                    "opr": ["Alert.LastTime", "$Last,?Hour6,DV,DV"],
                    "exp": None,
                },
                {
                    "opt": "EQUALS",
                    "opr": ["Alert.IPSID", "144115188075855872/8"],
                    "exp": None,
                },
                {
                    "opt": "OR",
                    "opr": None,
                    "exp": [
                        {
                            "opt": "EQUALS",
                            "opr": ["Alert.SrcIP", "{source_ip}"],
                            "exp": None,
                        },
                        {
                            "opt": "EQUALS",
                            "opr": ["Alert.DstIP", "{dest_ip}"],
                            "exp": None,
                        },
                    ],
                },
            ],
        },
        "groups": {},
        "orders": {
            "opt": "ORDER",
            "opr": None,
            "exp": [
                {"opt": "DESC", "opr": ["7"], "exp": None},
                {"exp": None, "opr": ["1"], "opt": "DESC"},
            ],
        },
    },
    "customOptions": {"requireTimeFrame": False},
    "queryParameters": [],
    "limit": 200,
    "offset": 0,
    "reverse": False,
    "getTotal": True,
}

# UI query component that has to be field to the main query above for fetching events for address type entity.
SEARCH_BY_ADDRESS_QUERY_COMPONENT = [
    {"opt": "EQUALS", "opr": ["Alert.SrcIP", "{0}"], "exp": None},
    {"opt": "EQUALS", "opr": ["Alert.DstIP", "{0}"], "exp": None},
]

# UI query component that has to be field to the main query above for fetching events for user type entity.
SEARCH_BY_USER_QUERY_COMPONENT = [
    {"opt": "EQUALS", "opr": ["Alert.6", "@{0}"], "exp": None},
    {"opt": "EQUALS", "opr": ["Alert.7", "@{0}"], "exp": None},
    {"opt": "EQUALS", "opr": ["Alert.4259860", "{0}"], "exp": None},
]

# UI query component that has to be field to the main query above for fetching events for host type entity.
SEARCH_BY_HOST_QUERY_COMPONENT = [
    {"opt": "EQUALS", "opr": ["Alert.65539", "{0}"], "exp": None},
    {"opt": "EQUALS", "opr": ["Alert.65575", "{0}"], "exp": None},
    {"opt": "EQUALS", "opr": ["Alert.4", "@{0}"], "exp": None},
    {"opt": "EQUALS", "opr": ["Alert.65628", "{0}"], "exp": None},
]

CORRELATIONS_TIME_FORMAT = "%m/%d/%Y %H:%M:%S"
MIN_TIME_ZONE = -11
MAX_TIME_ZONE = 14
# Following alarm names should always be ingested, regardless if they have source events or not
WHITELISTED_ALARM_NAMES = ["Device Health", "EPS Rate Exceeded"]

# Send Advanced Query To ESM
SEND_ADVANCED_QUERY_TO_ESM_SCRIPT_NAME = "Send Advanced Query To ESM"
TIME_TO_SLEEP_FUNCTION_IN_SECONDS = 5
QUERY_RESULTS_LIMIT = 5000
DEFAULT_IPSID = "144115188075855872/8"

QUERY_TEMPLATE_FOR_CONNECTOR = {
    "customOptions": {"requireTimeFrame": False},
    "getTotal": True,
    "limit": QUERY_RESULTS_LIMIT,
    "offset": 0,
    "query": {
        "fields": {
            "exp": None,
            "opr": [
                "Alert.IPSIDAlertID",
                "Alert.LastTime",
                "Action.DSIDSigID",
                "Rule.msg",
                "Alert.AvgSeverity",
            ],
            "opt": "SELECT",
        },
        "filters": {
            "exp": [
                {
                    "exp": None,
                    "opr": ["Alert.LastTime", "{start_time},DV,{end_time},DV"],
                    "opt": "EQUALS",
                },
                {
                    "exp": None,
                    "opr": ["Alert.IPSID", "144115188075855872/8"],
                    "opt": "EQUALS",
                },
            ],
            "opr": None,
            "opt": "AND",
        },
        "groups": {},
        "orders": {
            "exp": [
                {"exp": None, "opr": ["2"], "opt": "ASC"},
                {"exp": None, "opr": ["1"], "opt": "ASC"},
            ],
            "opr": None,
            "opt": "ORDER",
        },
        "sources": {
            "exp": [
                {"exp": [], "opr": ["QUERYID", "6"], "opt": "EQUALS"},
                {"exp": [], "opr": ["ESMQUERYTYPE", "EVENT"], "opt": "EQUALS"},
                {
                    "exp": [],
                    "opr": ["ESMQUERYDEVICESOURCE", "Alert.IPSID"],
                    "opt": "EQUALS",
                },
            ],
            "opr": [],
            "opt": "SOURCE",
        },
    },
    "queryParameters": [],
    "reverse": False,
}

TIME_FILTER_TEMPLATE = "{start_time},DV,{end_time},DV"

SEVERITY_FILTER_TEMPLATE = {
    "exp": None,
    "opr": ["Alert.AvgSeverity", ""],
    "opt": "GREATER_THAN",
}

SIGIDS_FILTER_TEMPLATE = {"exp": None, "opr": ["Alert.DSIDSigID", ""], "opt": "EQUALS"}

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
INTEGRATION_NAME = "LogRhythm"

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
ADD_ALARM_TO_CASE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Alarm To Case"
GET_ALARM_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Alarm Details"
ADD_NOTE_TO_CASE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Note To Case"
ADD_COMMENT_TO_ALARM_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Comment To Alarm"
LIST_ENTITY_EVENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Entity Events"
LIST_CASE_EVIDENCE_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Case Evidence"
UPDATE_ALARM_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Alarm"
DOWNLOAD_CASE_FILES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Download Case Files"
UPDATE_CASE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Case"
ATTACH_FILE_TO_CASE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Attach File To Case"
CREATE_CASE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Case"

# CONNECTORS NAMES
CASES_CONNECTOR_NAME = "LogRhythm Cases Connector"

# JOBS NAMES
SYNC_CASE_COMMENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Case Comments"
SYNC_ALARM_COMMENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Alarm Comments"
SYNC_CLOSED_CASES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Closed Cases"
SYNC_CLOSED_ALARMS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Closed Alarms"
# REST Alarms Connector
REST_ALARMS_CONNECTOR_SCRIPT_NAME = "LogRhythm - Rest API Alarms Connector"
DEFAULT_MAX_ALARMS_TO_FETCH = 10
DEFAULT_MAX_HOURS_BACKWARDS = 1
REST_ALARMS_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

INFO_SIEMPLIFY_SEVERITY = -1
LOW_SIEMPLIFY_SEVERITY = 40
MEDIUM_SIEMPLIFY_SEVERITY = 60
HIGH_SIEMPLIFY_SEVERITY = 80
CRITICAL_SIEMPLIFY_SEVERITY = 100
VALID_STATUS_CODES = 200
DEFAULT_RESULTS_LIMIT = 50
CASE_STATUS_OPEN = 1
CASE_STATUS_CLOSED = 2
LOGRHYTHM_COMPLETED_STATUS = 2
LOGRHYTHM_RESOLVED_STATUS = 5
LOGRHYTHM_MITIGATED_STATUS = 4
ALERTS_LIMIT = 10
DEFAULT_DAYS_BACKWARDS = 1

DEFAULT_DEVICE_PRODUCT = "LogRhythm"
DEVICE_VENDOR = "LogRhythm"
LOGRHYTHM_COMMENT_PREFIX = "LogRhythm: "
SIEMPLIFY_COMMENT_PREFIX = "Siemplify: "
LOGRHYTHM_ALERT_COMMENTS_PREFIX = "Comment: "
REASON = "Maintenance"
ROOT_CAUSE = "None"
COMMENT = "{0} in LogRhythm"
DEFAULT_ALERT_NAME = "LogRhythm Alert"
CASE_TYPE = "Case"
EVIDENCE_TYPE = "Evidence"
CASES_STATUS_NUMBER_DEFAULT = "1,3"
CASES_COUNT_DEFAULT = 100

UNIX_FORMAT = 1
DATETIME_FORMAT = 2

# TABLES NAMES
ALARM_EVENT_TABLE_NAME = "Alarm {id} Events"
CASE_EVIDENCE_TABLE_NAME = "Case {} Evidence"

ALARM_CLOSED_STATUS_LIST = [
    "Closed",
    "Closed: False Alarm",
    "Closed: Resolved",
    "Closed: Unresolved",
    "Closed: Reported",
    "Closed: Monitor",
]

ALARM_STATUS_MAPPING = {
    "New": "New",
    "Open": "Opened",
    "Working": "Working",
    "Escalated": "Escalated",
    "Closed": "Closed",
    "False Alarm": "Closed_FalseAlarm",
    "Resolved": "Closed_Resolved",
    "Unresolved": "Closed_Unresolved",
    "Reported": "Closed_Reported",
    "Monitor": "Closed_Monitor",
}

TYPE_OF_EVIDENCE_MAPPING = {
    "alarm": "alarm",
    "userevents": "userEvents",
    "log": "log",
    "note": "note",
    "file": "file",
}

SORT_ORDER_MAPPING = {
    "Datetime ASC": "PagedSortedDateAsc",
    "Datetime DESC": "PagedSortedDateDesc",
    "Risk ASC": "PagedSortedRiskAsc",
    "Risk DESC": "PagedSortedRiskDesc",
}

LIST_OF_STATUS_EVIDENCE = ["pending", "completed", "failed"]

TIME_FRAME_MAPPING = {
    "Last Hour": 3600000,
    "Last 6 Hours": 21600000,
    "Last 24 Hours": 86400000,
    "Last Week": 604800000,
    "Last Month": 2592000000,
}


CASE_STATUS_MAPPING = {
    "Created": 1,
    "Completed": 2,
    "Incident": 3,
    "Mitigated": 4,
    "Resolved": 5,
}

CASE_PRIORITY_MAPPING = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}

PRIORITY_MAPPING = {"1": 100, "2": 80, "3": 60, "4": 40, "5": -1}

WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2


PIFTypes_MAPPING = {
    1: {"Field Name": "Direction", "Friendly Name": "Direction"},
    2: {"Field Name": "Priority", "Friendly Name": "Priority"},
    3: {"Field Name": "NormalMsgDate", "Friendly Name": "Normal Message Date"},
    4: {
        "Field Name": "FirstNormalMsgDate",
        "Friendly Name": "First Normal Message Date",
    },
    5: {"Field Name": "LastNormalMsgDate", "Friendly Name": "Last Normal Message Date"},
    6: {"Field Name": "Count", "Friendly Name": "Count"},
    7: {"Field Name": "MsgDate", "Friendly Name": "MessageDate"},
    8: {"Field Name": "Entity", "Friendly Name": "Entity"},
    9: {"Field Name": "MsgSource", "Friendly Name": "Log Source"},
    10: {"Field Name": "MsgSourceHost", "Friendly Name": "Log Source Host"},
    11: {"Field Name": "MsgSourceType", "Friendly Name": "Log Source Type"},
    12: {"Field Name": "MsgClassType", "Friendly Name": "Log Class Type"},
    13: {"Field Name": "MsgClass", "Friendly Name": "Log Class"},
    14: {"Field Name": "CommonEvent", "Friendly Name": "Common Event"},
    15: {"Field Name": "MPERule", "Friendly Name": "MPE Rule"},
    16: {"Field Name": "Source", "Friendly Name": "Source"},
    17: {"Field Name": "Destination", "Friendly Name": "Destination"},
    18: {"Field Name": "Service", "Friendly Name": "Service"},
    19: {"Field Name": "KnownHost", "Friendly Name": "Known Host"},
    20: {"Field Name": "KnownSHost", "Friendly Name": "Known Host (Origin)"},
    21: {"Field Name": "KnownDHost", "Friendly Name": "Known Host (Impacted)"},
    22: {"Field Name": "KnownService", "Friendly Name": "Known Service"},
    23: {"Field Name": "IP", "Friendly Name": "IP"},
    24: {"Field Name": "SIP", "Friendly Name": "IP Address (Origin)"},
    25: {"Field Name": "DIP", "Friendly Name": "IP Address (Impacted)"},
    26: {"Field Name": "HostName", "Friendly Name": "Host Name"},
    27: {"Field Name": "SHostName", "Friendly Name": "Host Name (Origin)"},
    28: {"Field Name": "DHostName", "Friendly Name": "Host Name (Impacted)"},
    29: {"Field Name": "SPort", "Friendly Name": "Port (Origin)"},
    30: {"Field Name": "DPort", "Friendly Name": "Port (Impacted)"},
    31: {"Field Name": "Protocol", "Friendly Name": "Protocol"},
    32: {"Field Name": "Login", "Friendly Name": "User (Origin)"},
    33: {"Field Name": "Account", "Friendly Name": "User (Impacted)"},
    34: {"Field Name": "Sender", "Friendly Name": "Sender"},
    35: {"Field Name": "Recipient", "Friendly Name": "Recipient"},
    36: {"Field Name": "Subject", "Friendly Name": "Subject"},
    37: {"Field Name": "Object", "Friendly Name": "Object"},
    38: {"Field Name": "VendorMessageID", "Friendly Name": "Vendor Message ID"},
    39: {"Field Name": "VendorMessageName", "Friendly Name": "Vendor Message Name"},
    40: {"Field Name": "BytesIn", "Friendly Name": "Bytes In"},
    41: {"Field Name": "BytesOut", "Friendly Name": "Bytes Out"},
    42: {"Field Name": "ItemsIn", "Friendly Name": "Items In"},
    43: {"Field Name": "ItemsOut", "Friendly Name": "Items Out"},
    44: {"Field Name": "Duration", "Friendly Name": "Duration"},
    45: {"Field Name": "TimeStart", "Friendly Name": "Time Start"},
    46: {"Field Name": "TimeEnd", "Friendly Name": "Time End"},
    47: {"Field Name": "Process", "Friendly Name": "Process"},
    48: {"Field Name": "Amount", "Friendly Name": "Amount"},
    49: {"Field Name": "Quantity", "Friendly Name": "Quantity"},
    50: {"Field Name": "Rate", "Friendly Name": "Rate"},
    51: {"Field Name": "Size", "Friendly Name": "Size"},
    52: {"Field Name": "Domain", "Friendly Name": "Domain (Impacted)"},
    53: {"Field Name": "Group", "Friendly Name": "Group"},
    54: {"Field Name": "URL", "Friendly Name": "URL"},
    55: {"Field Name": "Session", "Friendly Name": "Session"},
    56: {"Field Name": "Sequence", "Friendly Name": "Sequence"},
    57: {"Field Name": "SNetwork", "Friendly Name": "Network (Origin)"},
    58: {"Field Name": "DNetwork", "Friendly Name": "Network (Impacted)"},
    59: {"Field Name": "SLocation", "Friendly Name": "Location (Origin)"},
    60: {"Field Name": "SLocationCountry", "Friendly Name": "Country (Origin)"},
    61: {"Field Name": "SLocationRegion", "Friendly Name": "Region (Origin)"},
    62: {"Field Name": "SLocationCity", "Friendly Name": "City (Origin)"},
    63: {"Field Name": "DLocation", "Friendly Name": "Location (Impacted)"},
    64: {"Field Name": "DLocationCountry", "Friendly Name": "Country (Impacted)"},
    65: {"Field Name": "DLocationRegion", "Friendly Name": "Region (Impacted)"},
    66: {"Field Name": "DLocationCity", "Friendly Name": "City (Impacted)"},
    67: {"Field Name": "SEntity", "Friendly Name": "Entity (Origin)"},
    68: {"Field Name": "DEntity", "Friendly Name": "Entity (Impacted)"},
    69: {"Field Name": "SZone", "Friendly Name": "Zone (Origin)"},
    70: {"Field Name": "DZone", "Friendly Name": "Zone (Impacted)"},
    72: {"Field Name": "Zone", "Friendly Name": "Zone"},
    73: {"Field Name": "User", "Friendly Name": "User"},
    74: {"Field Name": "Address", "Friendly Name": "Address"},
    75: {"Field Name": "MAC", "Friendly Name": "MAC"},
    76: {"Field Name": "NATIP", "Friendly Name": "NATIP"},
    77: {"Field Name": "Interface", "Friendly Name": "Interface"},
    78: {"Field Name": "NATPort", "Friendly Name": "NATPort"},
    79: {
        "Field Name": "SEntityOrDEntity",
        "Friendly Name": "Entity (Impacted or Origin)",
    },
    80: {"Field Name": "RootEntity", "Friendly Name": "RootEntity"},
    100: {"Field Name": "Message", "Friendly Name": "Message"},
    200: {"Field Name": "MediatorMsgID", "Friendly Name": "MediatorMsgID"},
    201: {"Field Name": "MARCMsgID", "Friendly Name": "MARCMsgID"},
    1040: {"Field Name": "SMAC", "Friendly Name": "MAC (Origin)"},
    1041: {"Field Name": "DMAC", "Friendly Name": "MAC (Impacted)"},
    1042: {"Field Name": "SNATIP", "Friendly Name": "NATIP (Origin)"},
    1043: {"Field Name": "DNATIP", "Friendly Name": "NATIP (Impacted)"},
    1044: {"Field Name": "SInterface", "Friendly Name": "Interface (Origin)"},
    1045: {"Field Name": "DInterface", "Friendly Name": "Interface (Impacted)"},
    1046: {"Field Name": "PID", "Friendly Name": "PID"},
    1047: {"Field Name": "Severity", "Friendly Name": "Severity"},
    1048: {"Field Name": "Version", "Friendly Name": "Version"},
    1049: {"Field Name": "Command", "Friendly Name": "Command"},
    1050: {"Field Name": "ObjectName", "Friendly Name": "ObjectName"},
    1051: {"Field Name": "SNATPort", "Friendly Name": "NATPort (Origin)"},
    1052: {"Field Name": "DNATPort", "Friendly Name": "NATPort (Impacted)"},
    1053: {"Field Name": "DomainOrigin", "Friendly Name": "Domain (Origin)"},
    1054: {"Field Name": "Hash", "Friendly Name": "Hash"},
    1055: {"Field Name": "Policy", "Friendly Name": "Policy"},
    1056: {"Field Name": "VendorInfo", "Friendly Name": "Vendor Info"},
    1057: {"Field Name": "Result", "Friendly Name": "Result"},
    1058: {"Field Name": "ObjectType", "Friendly Name": "Object Type"},
    1059: {"Field Name": "CVE", "Friendly Name": "CVE"},
    1060: {"Field Name": "UserAgent", "Friendly Name": "UserAgent"},
    1061: {"Field Name": "ParentProcessId", "Friendly Name": "Parent Process Id"},
    1062: {"Field Name": "ParentProcessName", "Friendly Name": "Parent Process Name"},
    1063: {"Field Name": "ParentProcessPath", "Friendly Name": "Parent Process Path"},
    1064: {"Field Name": "SerialNumber", "Friendly Name": "Serial Number"},
    1065: {"Field Name": "Reason", "Friendly Name": "Reason"},
    1066: {"Field Name": "Status", "Friendly Name": "Status"},
    1067: {"Field Name": "ThreatId", "Friendly Name": "Threat Id"},
    1068: {"Field Name": "ThreatName", "Friendly Name": "Threat Name"},
    1069: {"Field Name": "SessionType", "Friendly Name": "Session Type"},
    1070: {"Field Name": "Action", "Friendly Name": "Action"},
    1071: {"Field Name": "ResponseCode", "Friendly Name": "Response Code"},
    1072: {
        "Field Name": "UserOriginIdentityID",
        "Friendly Name": "User (Origin) Identity ID",
    },
    1073: {
        "Field Name": "UserImpactedIdentityID",
        "Friendly Name": "User (Impacted) Identity ID",
    },
    1074: {"Field Name": "SenderIdentityID", "Friendly Name": "Sender Identity ID"},
    1075: {
        "Field Name": "RecipientIdentityID",
        "Friendly Name": "Recipient Identity ID",
    },
    1076: {
        "Field Name": "UserOriginIdentity",
        "Friendly Name": "User (Origin) Identity",
    },
    1077: {
        "Field Name": "UserImpactedIdentity",
        "Friendly Name": "User (Impacted) Identity",
    },
    1078: {"Field Name": "SenderIdentity", "Friendly Name": "Sender Identity"},
    1079: {"Field Name": "RecipientIdentity", "Friendly Name": "Recipient Identity"},
    1080: {
        "Field Name": "UserOriginIdentityDomain",
        "Friendly Name": "User (Origin) Identity Domain",
    },
    1081: {
        "Field Name": "UserImpactedIdentityDomain",
        "Friendly Name": "User (Impacted) Identity Domain",
    },
    1082: {
        "Field Name": "SenderIdentityDomain",
        "Friendly Name": "Sender Identity Domain",
    },
    1083: {
        "Field Name": "RecipientIdentityDomain",
        "Friendly Name": "Recipient Identity Domain",
    },
    1084: {
        "Field Name": "UserOriginIdentityCompany",
        "Friendly Name": "User (Origin) Identity Company",
    },
    1085: {
        "Field Name": "UserImpactedIdentityCompany",
        "Friendly Name": "User (Impacted) Identity Company",
    },
    1086: {
        "Field Name": "SenderIdentityCompany",
        "Friendly Name": "Sender Identity Company",
    },
    1087: {
        "Field Name": "RecipientIdentityCompany",
        "Friendly Name": "Recipient Identity Company",
    },
    1088: {
        "Field Name": "UserOriginIdentityDepartment",
        "Friendly Name": "User (Origin) Identity Department",
    },
    1089: {
        "Field Name": "UserImpactedIdentityDepartment",
        "Friendly Name": "User (Impacted) Identity Department",
    },
    1090: {
        "Field Name": "SenderIdentityDepartment",
        "Friendly Name": "Sender Identity Department",
    },
    1091: {
        "Field Name": "RecipientIdentityDepartment",
        "Friendly Name": "Recipient Identity Department",
    },
    1092: {
        "Field Name": "UserOriginIdentityTitle",
        "Friendly Name": "User (Origin) Identity Title",
    },
    1093: {
        "Field Name": "UserImpactedIdentityTitle",
        "Friendly Name": "User (Impacted) Identity Title",
    },
    1094: {
        "Field Name": "SenderIdentityTitle",
        "Friendly Name": "Sender Identity Title",
    },
    1095: {
        "Field Name": "RecipientIdentityTitle",
        "Friendly Name": "Recipient Identity Title",
    },
    10001: {
        "Field Name": "SourceOrDestination",
        "Friendly Name": "Source Or Destination",
    },
    10002: {"Field Name": "SPortOrDPort", "Friendly Name": "Port (Origin or Impacted)"},
    10003: {
        "Field Name": "SNetworkOrDNetwork",
        "Friendly Name": "Network (Origin or Impacted)",
    },
    10004: {
        "Field Name": "SLocationOrDLocation",
        "Friendly Name": "Location (Origin or Impacted)",
    },
    10005: {
        "Field Name": "SLocationCountryOrDLocationCountry",
        "Friendly Name": "Country (Origin or Impacted)",
    },
    10006: {
        "Field Name": "SLocationRegionOrDLocationRegion",
        "Friendly Name": "Region (Origin or Impacted)",
    },
    10007: {
        "Field Name": "SLocationCityOrDLocationCity",
        "Friendly Name": "City (Origin or Impacted)",
    },
    10008: {"Field Name": "BytesInOut", "Friendly Name": "Bytes In/Out"},
    10009: {"Field Name": "ItemsInOut", "Friendly Name": "Items In/Out"},
}

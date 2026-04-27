from __future__ import annotations
INTEGRATION_NAME = "Cybereason"


# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ALLOW_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Allow File"
CLEAR_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Clear Reputation"
PREVENT_FILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Prevent File"
LIST_MALOP_AFFECTED_MACHINES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - List Malop Affected Machines"
)
ADD_COMMENT_TO_MALOP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Comment To Malop"
LIST_FILES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List files"
GET_MALOP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Malop"
SET_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Set Reputation"
UPDATE_MALOP_STATUS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Malop Status"
LIST_REPUTATION_ITEMS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Reputation Items"
ISOLATE_MACHINE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Isolate Machine"
UNISOLATE_MACHINE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Unisolate Machine"
LIST_MALOP_PROCESSES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Malop Processes"
IS_PROBE_CONNECTED_SCRIPT_NAME = f"{INTEGRATION_NAME} - Is Probe Connected"
LIST_PROCESSES_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Processes"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
EXECUTE_SIMPLE_INVESTIGATION_SEARCH_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Execute Simple Investigation Search"
)
GET_SENSOR_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Sensor Details"
REMEDIEATE_MELOP_SCRIPT_NAME = f"{INTEGRATION_NAME} - Remediate Melop"
LIST_MALOP_REMEDIATIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Malop Remediations"
# CONNECTOR NAMES
ALERTS_CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_NAME} - Malops Inbox Connector"

# TABLES NAMES
MALOP_CASE_WALL_NAME = "Malop {}"
REPUTATION_CASE_WALL_NAME = "Available Reputation Items"
MACHINES_CASE_WALL_NAME = "Affected Machines"

DEFAULT_TIMEOUT = 300

FILE_FIELDS = [
    "md5String",
    "ownerMachine",
    "avRemediationStatus",
    "isSigned",
    "signatureVerified",
    "sha1String",
    "maliciousClassificationType",
    "createdTime",
    "modifiedTime",
    "size",
    "correctedPath",
    "productName",
    "productVersion",
    "companyName",
    "internalName",
    "elementDisplayName",
]

PROCESS_FIELDS = [
    "elementDisplayName",
    "imageFile.maliciousClassificationType",
    "creationTime",
    "endTime",
    "commandLine",
    "isImageFileSignedAndVerified",
    "productType",
    "children",
    "parentProcess",
    "ownerMachine",
    "calculatedUser",
    "imageFile",
    "imageFile.sha1String",
    "imageFile.md5String",
    "imageFile.companyName",
    "imageFile.productName",
    "iconBase64",
    "ransomwareAutoRemediationSuspended",
    "executionPrevented",
    "isWhiteListClassification",
    "matchedWhiteListRuleIds",
    "pid",
]

SHA1 = "sha1"
MD5 = "md5"

SUSPICIOUS_TYPES = ["ransomware", "maltool", "unwanted", "malware", "blacklist"]
SUPPORTED_FILE_HASH_TYPES = [SHA1, MD5]
WHITELIST = "Whitelist"
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"

STATUSES = {
    "To Review": "TODO",
    "Remediated": "CLOSED",
    "Unread": "UNREAD",
    "Not Relevant": "FP",
    "Open": "OPEN",
}

NULL_SEVERITY = "N/A"
SEVERITIES = [NULL_SEVERITY, "Low", "Medium", "High"]

FAILURE_STATUS = "FAILURE"
QUERY_FILTER_DELIMITER = "\n"
QUERY_FILTER_ITEMS_DELIMITER = " "
QUERY_FILTER_VALUES_DELIMITER = " OR "
QUERY_FILTER_ITEMS_REQUIRED_COUNT = 3
REQUEST_TYPE_MAPPING = {
    "Machine": "Machine",
    "User": "User",
    "Process": "Process",
    "File": "File",
    "Connection": "Connection",
    "Domain Name": "DomainName",
    "IP Address": "IpAddress",
    "Service": "Service",
}

QUERIES_KEY = "queries"
REQUEST_TYPE_KEY = "request_type"
CONNECTION_KEY = "connection"
FILTER_OPERATORS = {"equals": "equals"}

IP_SENSOR_KEY = "internalIpAddress"
HOSTNAME_SENSOR_KEY = "fqdn"

REMEDEIATION_SUCCESS = "SUCCESS"
BLOCK_ACTION_LIST = ["BLOCK_FILE", "KILL_PREVENT_UNSUSPEND"]
RESPONSE_KEY_CHECK = "end"

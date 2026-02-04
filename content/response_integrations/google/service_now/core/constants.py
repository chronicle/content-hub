from __future__ import annotations

INTEGRATION_NAME = "ServiceNow"
PRODUCT_NAME = VENDOR = "Service Now"

# ACTION NAMES
ADD_ATTACHMENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Attachment"
ADD_COMMENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Comment"
ADD_COMMENT_AND_WAIT_FOR_REPLY_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Comment And Wait For Reply"
CLOSE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Close Incident"
CREATE_ALERT_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Alert Incident"
CREATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Incident"
CREATE_RECORD_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Record"
GET_CMDB_RECORDS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get CMDB Records Details"
GET_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Incident"
LIST_CMDB_RECORDS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List CMDB Records"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
UPDATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Incident"
UPDATE_RECORD_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update Record"
WAIT_FOR_FIELD_UPDATE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Wait For Field Update"
WAIT_FOR_STATUS_UPDATE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Wait For Status Update"
DOWNLOAD_ATTACHMENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Download Attachments"
GET_RECORD_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Record Details"
LIST_RECORDS_RELATED_TO_USER_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Records Related To User"
GET_USER_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get User Details"
GET_CHILD_INCIDENT_DETAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Child Incident Details"
GET_OAUTH_TOKEN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Oauth Token"
ADD_COMMENT_TO_RECORD_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Comment To Record"
WAIT_FOR_COMMENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Wait For Comments"
LIST_RECORD_COMMENTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Record Comments"
ADD_PARENT_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Parent Incident"

# JOB NAMES
SYNC_CLOSURE = "ServiceNow - SyncClosure"
SYNC_COMMENTS = "ServiceNow - SyncComments"
SYNC_COMMENTS_BY_TAG = "ServiceNow - SyncTableRecordCommentsByTag"

# CONNECTOR NAMES
CONNECTOR_NAME = "ServiceNowConnector"

# CONNECTOR PARAMS
DEFAULT_DAYS_BACKWARDS = 2
MAX_INCIDENTS_PER_CYCLE = 10
DEFAULT_NAME = "ServiceNow"
MSG_ID_ERROR_MSG = "Can't get incident id"
NO_RESULTS = "No Record found"
SN_DEFAULT_DOMAIN = "global"
DEFAULT_EVENT_NAME = "ServiceNowEvent"
LINK_KEY = "link"

HIGH_PRIORITY = 80
MEDIUM_PRIORITY = 60
LOW_PRIORITY = 40
# In ServiceNow 1=high, 2=medium, 3=low
PRIORITY_MAPPING = {"1": HIGH_PRIORITY, "2": MEDIUM_PRIORITY, "3": LOW_PRIORITY}
EXCLUDE_INCIDENT_FIELDS = ["problem_id", "assigned_to", "cmdb_ci", "opened_by", "sys_user_group"]

# STATUSE
RESOLVED = "resolved"
CLOSED = "closed"
CANCELED = "canceled"
STATES = {
    "new": 1,
    "in progress": 2,
    "on hold": 3,
    "resolved": 6,
    "closed": 7,
    "canceled": 8,
}
STATES_NAMES = {
    STATES[RESOLVED]: "Resolved",
    STATES[CLOSED]: "Closed",
    STATES[CANCELED]: "Cancelled",
}

# FILENAMES
CSV_FILE_NAME = "Relations.csv"
USERS_CVS_FILE_NAME = "User Details"
CHILD_INCIDENTS_TABLE_NAME = "Child Incident Details"

# CASE OPTIONS
CASE_RULE_GENERATOR = "Service Now System"

DEFAULT_MAX_RECORDS_TO_RETURN = 50
DEFAULT_MAX_DAYS_TO_RETURN = 1

RECORD_COMMENT_TYPES = {"Comment": "comments", "Work Note": "work_notes"}

RECORD_COMMENT_TYPE_NAMES = {"Comment": "comments", "Work Note": "work notes"}

SERVICE_NOW_TAG = "ServiceNow {table_name}"
RECORDS_TAG = "ServiceNow TicketId:"
TAG_SEPARATOR = ":"
CASE_STATUS_CLOSED = 2
CASE_STATUS_OPEN = 1
SIEMPLIFY_COMMENT_PREFIX = "Siemplify: "
SN_COMMENT_PREFIX = f"{INTEGRATION_NAME}: "

GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

ADD_NEW_ATTACHMENT_MODE = "Add New Attachment"
OVERWRITE_EXISTING_ATTACHMENT = "Overwrite Existing Attachment"

# Sync Incidents Job
SYNC_INCIDENTS_JOB_NAME = "Sync Incidents Job"
SYNC_LEVEL = {"CASE": "Case", "ALERT": "Alert"}
OPEN_CASES_KEY = "open_cases"
INCIDENTS_SYNC_TAG = "ServiceNow Incident Sync"
TICKET_ID_CONTEXT_KEY = "TICKET_ID"
INCIDENT_NUMBERS_MAPPING_KEY = "incident_numbers_mapping"
INCIDENTS_KEY = "incidents"
RELATED_OBJECTS_MAPPING_KEY = "related_objects_mapping"
RELATED_OBJECTS_KEY = "related_objects"
AFFECTED_CIS_MAPPING_KEY = "affected_cis_mapping"
AFFECTED_CIS_KEY = "affected_cis"
SYNC_INCIDENTS_JOB_COMMENT_PREFIX = "Sync Incidents Job: "
SNOW_COMMENT_PREFIX = "ServiceNow:"
SIEM_COMMENT_PREFIX = "SecOps:"
SNOW_ATTACHMENT_PREFIX = "From ServiceNow:"
SIEM_ATTACHMENT_PREFIX = "From SecOps:"
CONTEXT_VALUE_CHUNK_SIZE = 1000
CONTEXT_VALUE_CHUNK_LIMIT = 2_500_000
INCIDENTS_CONTEXT_VALUE_CHUNK_SIZE = 700
RELATED_OBJECTS_CONTEXT_VALUE_CHUNK_SIZE = 900
AFFECTED_CIS_CONTEXT_VALUE_CHUNK_SIZE = 700
PROCESSED_CASES_TIMESTAMP_KEY = "processed_cases_timestamp"
FIELDS_TO_EXCLUDE = [
    "sys_updated_on",
    "sys_updated_by",
    "sys_created_on",
    "sys_created_by",
    "sys_mod_count",
    "sys_tags",
    "sys_class_name",
    "sys_domain_path",
    "work_notes",
    "comments",
    "comments_and_work_notes",
    "activity_due",
    "last_login_time",
    "last_login",
    "link",
]
CASE_ATTACHMENT_TYPE = 4
INCIDENTS_REQUEST_LIMIT = 300
AFFECTED_CIS_REQUEST_LIMIT = 300
TICKET_ID = "TICKET_ID"

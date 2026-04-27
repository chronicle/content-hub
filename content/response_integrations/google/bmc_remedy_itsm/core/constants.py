from __future__ import annotations
INTEGRATION_NAME = "BMC Remedy ITSM"
INTEGRATION_DISPLAY_NAME = "BMC Remedy ITSM"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
CREATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Create Incident"
UPDATE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Incident"
GET_INCIDENT_DETAILS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Incident Details"
ADD_WORK_NOTE_TO_INCIDENT_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Add Work Note To Incident"
)
DELETE_INCIDENT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delette Incident"
WAIT_FOR_INCIDENT_FIELDS_UPDATE_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Wait For Incident Fields Update"
)
GET_RECORD_DETAILS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Record Details"
CREATE_RECORD_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Create Record"
UPDATE_RECORD_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Update Record"
WAIT_FOR_RECORD_FIELDS_UPDATE_SCRIPT_NAME = (
    f"{INTEGRATION_DISPLAY_NAME} - Wait For Record Fields Update"
)
DELETE_RECORD_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Delete Record"

ENDPOINTS = {
    "login": "/api/jwt/login",
    "ping": "/api/arsys/v1/entry/HPD:IncidentInterface?limit=1&fields=values(Status)",
    "get_template": "/api/arsys/v1/entry/HPD:TemplateSPGLookUp",
    "create_incident": "/api/arsys/v1/entry/HPD:IncidentInterface_Create?fields=",
    "get_incident_details": "/api/arsys/v1/entry/HPD:IncidentInterface",
    "get_worknotes": "/api/arsys/v1/entry/HPD:WorkLog",
    "update_incident": "/api/arsys/v1/entry/HPD:IncidentInterface/{request_id}",
    "add_worknote_to_incident": "/api/arsys/v1/entry/HPD:WorkLog/",
    "delete_incident": "/api/arsys/v1/entry/HPD:Help Desk/{entry_id}",
    "get_record_details": "/api/arsys/v1/entry/{record_type}/{record_id}",
    "logout": "/api/jwt/logout",
    "get_incident_details_by_table": "/api/arsys/v1/entry/{table_name}",
    "update_incident_by_table": "/api/arsys/v1/entry/{table_name}/{request_id}",
    "create_record": "/api/arsys/v1/entry/{record_type}?fields=",
    "update_record": "/api/arsys/v1/entry/{record_type}/{record_id}",
    "delete_record": "/api/arsys/v1/entry/{record_type}/{record_id}",
}

# Job
SYNC_CLOSURE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync Closed Incidents By Tag"
BMC_REMEDY_ITSM_TAG = "BMC Remedy ITSM"
INCIDENTS_TAG = "BMC Remedy ITSM:"
TAG_SEPARATOR = ":"
CANCELLED_STATUS = "Cancelled"
CLOSED_STATUS = "Closed"
RESOLVED_STATUS = "Resolved"
REASON = "Maintenance"
ROOT_CAUSE = "Other"
COMMENT = "{status} in BMC Remedy ITSM"
CASE_STATUS_CLOSED = 2
CASE_STATUS_OPEN = 1
DEFAULT_HOURS_BACKWARDS = 24
MIN_HOURS_BACKWARDS = 1


STATUS_MAPPING = {
    "Select One": "",
    "New": "New",
    "Assigned": "Assigned",
    "In Progress": "In Progress",
    "Pending": "Pending",
    "Resolved": "Resolved",
    "Closed": "Closed",
    "Cancelled": "Cancelled",
}

IMPACT_MAPPING = {
    "Select One": "",
    "Extensive/Widespread": "1-Extensive/Widespread",
    "Significant/Large": "2-Significant/Large",
    "Moderate/Limited": "3-Moderate/Limited",
    "Minor/Localized": "4-Minor/Localized",
}

URGENCY_MAPPING = {
    "Select One": "",
    "Critical": "1-Critical",
    "High": "2-High",
    "Medium": "3-Medium",
    "Low": "4-Low",
}

REPORTED_SOURCE_MAPPING = {
    "Select One": "",
    "Direct Input": "Direct Input",
    "Email": "Email",
    "External Escalation": "External Escalation",
    "Fax": "Fax",
    "Self Service": "Self Service",
    "Systems Management": "Systems Management",
    "Phone": "Phone",
    "Voice Mail": "Voice Mail",
    "Walk In": "Walk In",
    "Web": "Web",
    "Other": "Other",
    "BMC Impact Manager Event": "BMC Impact Manager Event",
}

INCIDENT_TYPE_MAPPING = {
    "Select One": "",
    "User Service Restoration": "User Service Restoration",
    "User Service Request": "User Service Request",
    "Infrastructure Restoration": "Infrastructure Restoration",
    "Infrastructure Event": "Infrastructure Event",
}

PRIORITY_MAPPING = {
    ("1-Critical", "1-Extensive/Widespread"): "Critical",
    ("1-Critical", "2-Significant/Large"): "Critical",
    ("1-Critical", "3-Moderate/Limited"): "High",
    ("1-Critical", "4-Minor/Localized"): "High",
    ("2-High", "1-Extensive/Widespread"): "Critical",
    ("2-High", "2-Significant/Large"): "High",
    ("2-High", "3-Moderate/Limited"): "High",
    ("2-High", "4-Minor/Localized"): "Medium",
    ("3-Medium", "1-Extensive/Widespread"): "Medium",
    ("3-Medium", "2-Significant/Large"): "Medium",
    ("3-Medium", "3-Moderate/Limited"): "Medium",
    ("3-Medium", "4-Minor/Localized"): "Medium",
    ("4-Low", "1-Extensive/Widespread"): "Low",
    ("4-Low", "2-Significant/Large"): "Low",
    ("4-Low", "3-Moderate/Limited"): "Low",
    ("4-Low", "4-Minor/Localized"): "Low",
}

DEFAULT_WORK_NOTES_LIMIT = 50
INCIDENT_NUMBER_FIELD = "Incident Number"


ACTION_ITERATIONS_INTERVAL = 30 * 1000
ACTION_ITERATION_DURATION_BUFFER = 2 * 60 * 1000

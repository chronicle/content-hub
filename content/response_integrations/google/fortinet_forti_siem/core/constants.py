from __future__ import annotations
INTEGRATION_NAME = "Fortinet FortiSIEM"
INTEGRATION_DISPLAY_NAME = "Fortinet FortiSIEM"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Enrich Entities"
ADVANCED_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Advanced Query"
SIMPLE_QUERY_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Simple Query"

ENDPOINTS = {
    "ping": "/phoenix/rest/deviceInfo/monitoredDevices",
    "get_incidents": "/phoenix/rest/pub/incident",
    "get_incident_events": "/phoenix/rest/pub/incident/triggeringEvents",
    "get_device_info": "/phoenix/rest/cmdbDeviceInfo/device",
    "start_event_query": "/phoenix/rest/query/eventQuery",
    "get_event_query_progress": "/phoenix/rest/query/progress/{query_id}",
    "get_event_query_results": "/phoenix/rest/query/events/{query_id}/0/{limit}",
}

# Connector
CONNECTOR_NAME = "FortiSIEM Incidents Connector"
DEFAULT_TIME_FRAME = 24
DEFAULT_LIMIT = 10
DEVICE_VENDOR = "Fortinet"
DEVICE_PRODUCT = "Fortinet FortiSIEM"
DEFAULT_MAX_LIMIT = 100
EVENTS_DEFAULT_LIMIT = 100
INCIDENT_FIELDS = [
    "eventSeverityCat",
    "eventSeverity",
    "incidentLastSeen",
    "incidentFirstSeen",
    "eventType",
    "eventName",
    "incidentSrc",
    "incidentTarget",
    "incidentDetail",
    "incidentRptIp",
    "incidentRptDevName",
    "incidentStatus",
    "incidentComments",
    "customer",
    "incidentClearedReason",
    "incidentClearedTime",
    "incidentClearedUser",
    "count",
    "incidentId",
    "incidentSrc",
    "incidentTarget",
    "incidentExtUser",
    "incidentExtClearedTime",
    "incidentExtTicketId",
    "incidentExtTicketState",
    "incidentExtTicketType",
    "incidentReso",
    "phIncidentCategory",
    "phSubIncidentCategory",
    "incidentTitle",
    "attackTechnique",
    "attackTactic",
]

SEVERITY_MAP = {"INFO": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100}

QUERY_STATUS = {"completed": "100"}

CUSTOM_TIME_FRAME = "Custom"

TIMEFRAME_MAPPING = {
    "Last Hour": {"hours": 1},
    "Last 6 Hours": {"hours": 6},
    "Last 24 Hours": {"hours": 24},
    "Last Week": "last_week",
    "Last Month": "last_month",
    "Custom": "custom",
}

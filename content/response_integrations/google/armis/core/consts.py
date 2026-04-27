from __future__ import annotations
INTEGRATION_NAME = "Armis"
CONNECTOR_DISPLAY_NAME = "Armis - Alerts Connector"

# Actions names:
PING = "Ping"
ENRICH_ENTITIES = "Enrich Entities"
LIST_ALERT_CONNECTIONS = "List Alert Connections"
UPDATE_ALERT_STATUS = "Update Alert Status"


ARMIS_ENRICHMENT_PREFIX = "ARMS"
NOT_ASSIGNED = "N/A"
ENDPOINT_INSIGHT_TEMPLATE = """
<p style="margin-bottom: -10px;font-size:15px"><strong>Endpoint: {entity_identifier}</strong></p>
<b>Risk Level: <span style="color:{risk_color}">{risk_level}</span></b>
<b>IP Address:</b> {ip_address}
<b>Mac Address:</b> {mac_address}
<b>OS:</b> {os}
<b>User:</b> {user}
<b>Type:</b> {type}
<b>Site:</b> {site_name}
<b>Link:</b> {html_report_link}
"""
ENDPOINT_INSIGHT_TITLE = "Endpoint Information"
HTML_LINK = """<a href="{link}" target="_blank">{link}</a>"""
GREEN = "#12ab50"
ORANGE = "#f79420"
RED = "#ff0000"

TIMEOUT_THRESHOLD = 0.9
MIN_CONNECTIONS_TO_RETURN = 1
MAX_SIEMPLIFY_EVENTS = 200
MAX_ALERTS_TO_FETCH = 1000
DEFAULT_LENGTH_TO_FETCH = 100
DEFAULT_CONNECTIONS_TO_FETCH = 50
DEFAULT_ORDER_BY = "time"
DEFAULT_RISK_LEVELS = "Low,Medium"
DEFAULT_ALERT_FIELDS = "alertId,severity,title,type,status,time,description"
DEFAULT_STATUS = "Unhandled"
DEFAULT_SEVERITY = "Medium"

DEFAULT_AQL_GET_ALERT_WITH_TIME = "in:alerts after:{0} riskLevel:{1}"
DEFAULT_AQL_GET_ALERT_WITHOUT_TIME = "in:alerts riskLevel:{0}"
DEFAULT_AQL = "in:{0} alert:(alertId:({1}))"
DEVICES = "devices"
ACTIVITY = "activity"

DEFAULT_TIMEOUT_IN_SECONDS = 180
DEFAULT_HOURS_BACKWARDS = 1
DEFAULT_HOURS_BACKWARDS_FROM_EXISTING_IDS = 72
DEFAULT_LOWEST_SEVERITY_TO_FETCH = "Low"
DEFAULT_MAX_ALERTS_TO_FETCH = 10
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"

SEVERITIES = {"LOW": 40, "MEDIUM": 60, "HIGH": 80}

SEVERITIES_FILTER_MAPPING = {
    "LOW": "Low,Medium,High",
    "MEDIUM": "Medium,High",
    "HIGH": "High",
}

REQUEST_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

IDS_FILE = "ids.json"

ALERT_CONNECTIONS_TABLE = "Available Communications"

# Errors code:
BAD_REQUEST = 400
NOT_FOUND = 404

WASNT_FOUND = "wasn't found"

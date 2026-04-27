from __future__ import annotations
INTEGRATION_NAME = "TruSTAR"

#  Actions:
PING = "Ping"
ENRICH_ENTITIES = "Enrich Entities"
GET_RELATED_IOCS = "Get Related IOCs"
LIST_ENCLAVES = "List Enclaves"
GET_RELATED_REPORTS = "Get Related Reports"

#  Error codes:
UNAUTHORIZED_ERROR = 401

DEFAULT_SIZE_PAGE = 25
FIRST_PAGE_NUMBER = 0

DEFAULT_SECURITY_LEVEL_THRESHOLD = "Low"
ENCLAVE_FILTERS = "Enclave Filters"

SECURITY_LEVEL_MAPPING = {"BENIGN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

REVERES_SECURITY_LEVEL_MAPPING = {0: "Benign", 1: "Low", 2: "Medium", 3: "High"}

COLORS_SECURITY_LEVEL_MAPPING = {0: "#339966", 1: "#ffcc00", 2: "#ff9900", 3: "#ff0000"}

BENIGN_SEVERITY = "BENIGN"
LOW_SEVERITY = "LOW"
MEDIUM_SEVERITY = "MEDIUM"
HIGH_SEVERITY = "HIGH"

INTEGRATION_PREFIX = "TruS"
REPORT_LINK = "https://station.trustar.co/constellation/reports/{0}"

DEFAULT_MAX_RELATED_IOCS = 50
MAX_RELATED_IOCS = 1000
MIN_RELATED_IOCS = 0
DEFAULT_MAX_REPORTS = 10
MAX_REPORTS = 25
MIN_REPORTS = 0

REPORT_BASE_URL = "https://station.trustar.co/constellation/reports/{report_id}"
INSIGHT_HTML_TEMPLATE = """
<p style="margin-bottom: -10px;font-size:15px"><strong>Report: {title}</strong></p>
<b>Submitted:</b> {created}
<b>Updated:</b> {updated}
<b>Status:</b> {submission_status}
<b>Tags:</b> {tags}
<b>Link:</b> {link}
{report_body}
"""
REPORT_BODY_INSIGHT = """
<p style="margin-bottom: -10px;font-size:15px"><strong>Body</strong></p>
{report_body}
"""
NOT_ASSIGNED = "N/A"
HTML_LINK = """<a href="{link}" target="_blank">{link}</a>"""

DATE_FORMAT = "%Y-%m-%d %H:%M:%S %Z"
RELATED_REPORTS_CSV_TABLE_TITLE = "Related Reports"
EQUAL_ENCLAVE_FILTER_OPERATOR = "Equal"
CONTAINS_ENCLAVE_FILTER_OPERATOR = "Contains"
DEFAULT_MAX_ENCLAVES = 50

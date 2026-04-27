from __future__ import annotations
INTEGRATION_NAME = "QualysVM"
INTEGRATION_DISPLAY_NAME = "Qualys VM"


PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
DOWNLOAD_VM_SCAN_RESULTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - DownloadVmScanResults"
ENRICH_HOST_SCRIPT_NAME = f"{INTEGRATION_NAME} - EnrichHost"
FETCH_REPORT_SCRIPT_NAME = f"{INTEGRATION_NAME} - FetchReport"
LAUNCH_COMPLIANCE_REPORT_SCRIPT_NAME = f"{INTEGRATION_NAME} - LaunchComplianceReport"
LAUNCH_PATCH_REPORT_SCRIPT_NAME = f"{INTEGRATION_NAME} - LaunchPatchReport"
LAUNCH_REMEDIATION_REPORT_SCRIPT_NAME = f"{INTEGRATION_NAME} - LaunchRemediationReport"
LAUNCH_SCAN_REPORT_SCRIPT_NAME = f"{INTEGRATION_NAME} - LaunchScanReport"
LAUNCH_VM_SCAN_SCRIPT_NAME = f"{INTEGRATION_NAME} - LaunchVmScan"
LIST_GROUPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - ListGroups"
LIST_IPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - ListIps"
LIST_REPORTS_SCRIPT_NAME = f"{INTEGRATION_NAME} - ListReports"
LIST_SCANS_SCRIPT_NAME = f"{INTEGRATION_NAME} - ListScans"
LIST_ENDPOINT_DETECTIONS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Endpoint Detections"

ENDPOINTS = {
    "get_detections": "/api/4.0/fo/asset/host/vm/detection/",
    "find_hostname_ip": "/api/5.0/fo/asset/host/",
    "get_detection_details": "/api/4.0/fo/knowledge_base/vuln/",
    "report": "/api/3.0/fo/report/",
    "scan": "/api/3.0/fo/scan/",
}

FILTER_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# Connector
CONNECTOR_NAME = f"{INTEGRATION_DISPLAY_NAME} - Detections Connector"
DEFAULT_SEVERITY = 1
DEVICE_VENDOR = "Qualys"
DEVICE_PRODUCT = "Qualys VM"
STORED_IDS_LIMIT = 10000

SEVERITY_MAP = {1: -1, 2: 40, 3: 60, 4: 80, 5: 100}

DETECTION_SEVERITY_MAP = {
    "1": "Info",
    "2": "Low",
    "3": "Medium",
    "4": "High",
    "5": "Critical",
}

USER_DETECTION_SEVERITY_MAP = {
    "Info": 1,
    "Low": 2,
    "Medium": 3,
    "High": 4,
    "Critical": 5,
}
CRITICAL_SEVERITY = 5

SEVERITIES = [1, 2, 3, 4, 5]
HOST_GROUPING = "Host"
DETECTION_GROUPING = "Detection"
NONE_GROUPING = "None"
RULE_GENERATOR = "Qualys Vulnerability"
POSSIBLE_STATUSES = ["New", "Active", "Fixed", "Re-Opened"]
DEFAULT_STATUS_FILTER = "New,Active,Re-Opened"
POSSIBLE_GROUPINGS = [NONE_GROUPING, HOST_GROUPING, DETECTION_GROUPING]


SCAN_TEMPLATE = "Executive Report"
ENRICHMENT_PREFIX = "Qualys"

FINISH_STATE = "Finished"
ERROR_STATES = ["Error", "Canceled", "Paused"]

ENRICHMENT_INSIGHT_TEMPLATE = """
<p><strong>IP: </strong>{ip_address}<strong><br />NetBIOS: </strong>{netbios_name}<br /><strong>DNS Domain: </strong>{dns_domain}<strong><br />DNS FQDN:</strong>&nbsp;{dns_fqdn}<br /><strong>OS: </strong>{os}<br /><strong>Tags: </strong>{tags}<br /><strong>Comments: </strong>{comment}</p>

"""

LIST_ENDPOINT_DETECTIONS_INSIGHT_TEMPLATE = """
<h2><strong>Detection: {qid}. {title}. Severity: <span style="color: {color};">{criticality_level}</span></strong></h2>
<p><strong>Diagnosis</strong><br />{diagnosis}</p>
<p><strong>Consequences</strong><br />{consequence}</p>
<p><strong>Solution</strong><br />{solution}</p>

"""

SEVERITY_COLOR_MAP = {
    "Low": "#00ccff",
    "Medium": "#ffcc00",
    "High": "#ff9900",
    "Critical": "#ff0000",
}
MAX_DETECTIONS_TO_FETCH = 200

from __future__ import annotations
INTEGRATION_NAME = "SCC Enterprise"
SNAKE_INTEGRATION_NAME = "scc_enterprise"

# Action Script Names
CLOUD_ENTITY_PARSER_SCRIPT_NAME = "Cloud Entity Parser"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
PREPARE_DESC_SCRIPT_NAME = f"{INTEGRATION_NAME} - Prepare Description"
POPULATE_FINDINGS_CONTEXT_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Set SCC-FINDINGS-STATE Context Value"
)
SERVICE_NOW_BOOTSTRAP = (
    f"{INTEGRATION_NAME} - Create {INTEGRATION_NAME} Cloud Posture Ticket Type SNOW"
)
JIRA_BOOTSTRAP = (
    f"{INTEGRATION_NAME} - Create {INTEGRATION_NAME} Cloud Posture Ticket Type Jira"
)
LOCK_PLAYBOOK = f"{INTEGRATION_NAME} - Lock Playbook"
ADD_SCCE_TAGS = f"{INTEGRATION_NAME} - Add SCCE Tags"


# Connector Script Names
URGENT_POSTURE_CONNECTOR_NAME = f"{INTEGRATION_NAME} - Urgent Posture Finding Connector"

# Job Script Names
SYNC_DATA_JOB_NAME = f"{INTEGRATION_NAME} - Sync SCC Data Job"
SYNC_SCC_JIRA_TICKETS = f"{INTEGRATION_NAME} - SyncSCCJiraTickets"
SYNC_SCC_SNOW_TICKETS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Sync SCC-ServiceNow Tickets"

SCCE_COMMENT_PREFIX = f"{INTEGRATION_NAME}: "
CLOSED_BY_SCCE_COMMENT = f"Closed by {INTEGRATION_NAME}"

EXTERNAL_SCC_TICKET_INFO = "EXTERNAL-SCC-TICKET-INFO"
INTERNAL_SCC_TICKET_INFO = "INTERNAL-SCC-TICKET-INFO"
FINDINGS_CONTEXT_KEY = "SCC-FINDINGS-STATE"
SCC_SMART_LOCK = "SCC-SMART-LOCK"

CASE_FAILURE_BACKLOG_DB_KEY = "case_failure_backlog"
CASE_FAILURE_BACKLOG_FILE_NAME = f"{CASE_FAILURE_BACKLOG_DB_KEY}.json"
CASE_TICKET_MAP_DB_KEY = "case_ticket_map"
CASE_TICKET_MAP_FILE_NAME = f"{CASE_TICKET_MAP_DB_KEY}.json"
CASE_SLO_DAYS_INTERVALS = [0, 1, 3, 7, 14]
CASE_URL_TEMPLATE = "{ui_root}/cases/{case_id}"

BACKLOG_RETRIES_LIMIT = 3

NOT_AVAILABLE = "N/A"

HTML_TEMPLATE_TYPE = "HTML"
JWM_TEMPLATE_TYPE = "Jira Wiki Markup"


HTML_TEMPLATE_FILE_NAME = "html_template.html"
JWM_TEMPLATE_FILE_NAME = "jira_wiki_markup_template.html"

GCP = "GCP"
AWS = "AWS"
AZURE = "AZURE"
OTHER = "OTHER"
CLOUD_PROVIDER = "CLOUD_PROVIDER:{0}"
CLOUD_PROVIDER_GCP = CLOUD_PROVIDER.format(GCP)
CLOUD_PROVIDER_AWS = CLOUD_PROVIDER.format(AWS)
CLOUD_PROVIDER_AZURE = CLOUD_PROVIDER.format(AZURE)
CLOUD_PROVIDER_OTHER = CLOUD_PROVIDER.format(OTHER)

# language=pythonregexp
URL_REGEXP = r"https?://[-\w@:%.+~#=]{1,256}\.[\w()]{1,6}\b[-\w()@:%+.~#?&//=]*"
# language=pythonregexp
MD_HYPERLINK_REGEXP = (
    r"\[.*]\(https?://[-\w@:%.+~#=]{1,256}\.[\w()]{1,6}\b[-\w()@:%+.~#?&//=]*\)"
)
# language=pythonregexp
BACKTICK_WRAPPED_REGEXP = r"`[^`]+`"
# language=pythonregexp
CODE_TICK_WRAPPED_REGEXP = r"```[^`]+```"
# language=pythonregexp
TWO_STAR_WRAPPED_REGEXP = r"\*\*[^*]+\*\*"
# language=pythonregexp
CODE_BLOCK_DOUBLE_NL = r"```\w+\n[^`]*\n\n[^`]*```(?!\w)"
# language=pythonregexp
CODE_BLOCK_STYLE = r"```\w+\n"
# language=pythonregexp
NESTED_UNORDERED_LIST_REGEXP = r"\n\s{2,}\*"
# language=pythonregexp
NESTED_ORDERED_LIST_REGEXP = r"\n\s{2,}#"
# language=pythonregexp
TWO_INDENT_NESTED_UNORDERED_LIST_REGEXP = r"\n\s{2}\*"
# language=pythonregexp
TWO_INDENT_NESTED_ORDERED_LIST_REGEXP = r"\n\s{2}\d\."
# language=pythonregexp
MD_STRONG_REGEXP = r"( |\n|^)(__[^_\n]+__)( |\n|$)"
# language=pythonregexp
MD_ORDERED_LIST = r"\n\n( *\d\. .*\n)+"
# language=pythonregexp
MD_ORDERED_LIST_NUMBER = r"\d\."

X_EMOJI = chr(10_060)
V_EMOJI = chr(9_989)
MUTE_EMOJI = chr(128_263)

CASE_PRIORITY_TO_TICKET_SEVERITY = {
    "Informative": "Info",
    "Low": "Low",
    "Medium": "Medium",
    "High": "High",
    "Critical": "Critical",
}

# Statuses
OPEN_STATUS = "Open"
ASSIGNED_STATUS = "Assigned"
IN_PROGRESS_STATUS = "In Progress"
RESOLVED_STATUS = "Resolved"
WONT_DO_STATUS = "Won`t Do"

CLOSED_STATUSES = [RESOLVED_STATUS, WONT_DO_STATUS]

# SCCE OOTB Auth
OOTB_AUTH_ID_SCCE = "gcp_ootb_auth"
OOTB_AUTH_KEY_SCCE = "scc_sa_email"

FINDING_SEVERITY_COLOR_MAPPING = {
    "critical": "red",
    "high": "orange",
    "medium": "gold",
    "low": "dodgerblue",
    "unspecified": "",
}

TAG_MAPPING = {
    "cloudProvider": lambda value: {
        "GOOGLE_CLOUD_PLATFORM": ["Google Cloud", "GCP"],
        "AMAZON_WEB_SERVICES": "AWS",
        "MICROSOFT_AZURE": "Azure",
    }.get(value),
    "findingClass": lambda value: {
        "MISCONFIGURATION": "MISCONFIGURATION",
        "VULNERABILITY": "VULNERABILITY",
        "TOXIC_COMBINATION": "Toxic Combination",
    }.get(value),
    "parentDisplayName": lambda value: {
        "IAM Recommender": "CIEM",
        "CIEM": "CIEM",
    }.get(value),
    "resource_gcpMetadata_projectDisplayName": lambda value: f"Project: {value}",
    r"resource_gcpMetadata_folders_\d+_resourceFolderDisplayName": (
        lambda value: f"Folder: {value}"
    ),
    "resource_awsMetadata_account_name": lambda value: f"AWS Account: {value}",
    "resource_azureMetadata_resourceGroup_name": (
        lambda value: f"Azure Resource Group: {value}"
    ),
}

PROVIDER_NAME_CIEM = "PROVIDER_NAME_CIEM"

# Move to TIPCommon
WF_STATUS_INPROGRESS = 1
WF_STATUS_COMPLETED = 2
WF_STATUS_FAILED = 3
WF_STATUS_PENDING = 4
WF_STATUS_TERMINATED = 5

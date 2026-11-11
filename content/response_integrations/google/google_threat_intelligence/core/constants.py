from __future__ import annotations

from datetime import timedelta
from enum import Enum

from soar_sdk.SiemplifyDataModel import EntityTypes

INTEGRATION_IDENTIFIER = "GoogleThreatIntelligence"
INTEGRATION_DISPLAY_NAME = "Google Threat Intelligence"
INTEGRATION_PREFIX = "GTI_"

PING_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Ping"
GET_GRAPH_DETAILS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Graph Details"
SEARCH_GRAPHS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Search Graphs"
SEARCH_ENTITY_GRAPHS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Search Entity Graphs"
UPDATE_DTM_ALERT_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update DTM Alert"
ADD_COMMENT_TO_ENTITY_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Add Comment To Entity"
GET_ASM_ENTITY_DETAILS_SCRIPT_NAME = (
    f"{INTEGRATION_IDENTIFIER} - Get ASM Entity Details"
)
ADD_VOTE_TO_ENTITY_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Add Vote To Entity"
SEARCH_ASM_ISSUES_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Search ASM Issues"
SEARCH_ASM_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Search ASM Entities"
UPDATE_ASM_ISSUE_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update ASM Issue"
SET_DTM_ALERT_ANALYSIS_SCRIPT_NAME = (
    f"{INTEGRATION_IDENTIFIER} - Set DTM Alert Analysis"
)
GET_RELATED_ASSOCIATIONS_SCRIPT_NAME = (
    f"{INTEGRATION_IDENTIFIER} - Get Related Associations"
)
GET_RELATED_IOCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Related IOCs"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Enrich Entities"
EXECUTE_IOC_SEARCH_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Execute IOC Search"
DOWNLOAD_FILE_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Download File"
ENRICH_IOCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Enrich IOCs"
SUBMIT_FILE_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Submit File"
PRIVATE_SUBMIT_URL_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Private Submit URL"
ADD_ASM_ISSUE_NOTE_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Add ASM Issue Note"
ADD_TAG_TO_DTM_ALERT_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Add Tag To DTM Alert"
GTI_ALERTS_CONNECTOR_SCRIPT_NAME: str = (
    f"{INTEGRATION_IDENTIFIER} - GTI Alerts Connector"
)
GTI_IDP_TOKEN_URL: str = (
    "https://idp.prod.identity.proactive.virustotal.com/realms/master/exchange/api-key"
)

ASK_THREAT_INTELLIGENCE_AGENT_SCRIPT_NAME: str = (
    f"{INTEGRATION_IDENTIFIER} - Ask Threat Intelligence Agent"
)

ENDPOINTS: dict[str, str] = {
    "get_gti_alerts": "v1beta/projects/{project_id}/alerts",
    "search_gti_findings": "v1beta/projects/{project_id}/findings:search",
    "get_gti_finding": "v1beta/{finding_name}",
    "get_gti_alert_document": "v1beta/{document_name}",
    "create_agent_session": "api/v3/agentspace/sessions",
    "post_session_message": "api/v3/agentspace/sessions/{session_id}",
    "delete_agent_session": "api/v3/agentspace/sessions/{session_id}",
    "ping": "api/v3/metadata",
    "asm_ping": "api/v3/asm/projects",
    "get_graph_details": "api/v3/graphs/{graph_id}",
    "search_graphs": "api/v3/graphs",
    "update_dtm_alert": "api/v3/dtm/alerts/{alert_id}",
    "set_dtm_alert_analysis": "api/v3/dtm/alerts/{alert_id}/analysis",
    "upload_file_to_alerts_analysis": "api/v3/dtm/alerts/{alert_id}/attachments",
    "add_comment_address": "api/v3/ip_addresses/{identifier}/comments",
    "add_comment_url": "api/v3/urls/{identifier}/comments",
    "add_comment_filehash": "api/v3/files/{identifier}/comments",
    "add_comment_hostname": "api/v3/domains/{identifier}/comments",
    "add_comment_domain": "api/v3/domains/{identifier}/comments",
    "get_dtm_alerts": "api/v3/dtm/alerts",
    "list_dtm_monitors": "api/v3/dtm/monitors",
    "index_projects": "api/v3/asm/projects",
    "entity_full_details": "api/v3/asm/entities/{entity_id}/raw",
    "add_vote_address": "api/v3/ip_addresses/{identifier}/votes",
    "add_vote_url": "api/v3/urls/{identifier}/votes",
    "add_vote_filehash": "api/v3/files/{identifier}/votes",
    "add_vote_hostname": "api/v3/domains/{identifier}/votes",
    "add_vote_domain": "api/v3/domains/{identifier}/votes",
    "search_issues": "api/v3/asm/search/issues/{query_string}",
    "search_entities": "api/v3/asm/search/entities/{query_string}",
    "update_issue": "api/v3/asm/issues/{issue_id}/status",
    "get_issue_details": "api/v3/asm/issues/{issue_id}",
    "get_related_iocs": "api/v3/{type}/{id}/relationships/{relationship}",
    "get_iocs_for_threat_actors": "api/v3/{type}/{id}/{relationship}",
    "get_threat_actor": "api/v3/collections",
    "get_comments": "api/v3/{ioc_type}/{ioc}/comments",
    "get_ioc_details": "api/v3/{ioc_type}/{ioc}",
    "private_get_ioc_details": "api/v3/private/{ioc_type}/{ioc}",
    "vulnerability_details": "api/v3/collections/vulnerability--{vulnerability}",
    "get_widget": "api/v3/gtiwidget",
    "get_sandbox_data": "api/v3/file_behaviours/{hash}_{sandbox}",
    "get_mitre": "api/v3/files/{entity}/behaviour_mitre_trees",
    "urls": "api/v3/urls",
    "private_urls": "api/v3/private/urls",
    "submit_hash_analysis": "api/v3/files/{hash}/analyse",
    "analyses": "api/v3/analyses/{analysis_id}",
    "analyses-private": "api/v3/private/analyses/{analysis_id}",
    "search_ioc": "api/v3/intelligence/search",
    "ioc_stream": "api/v3/ioc_stream",
    "get_file": "api/v3/files/{entity_hash}/download",
    "file-upload-url": "api/v3/files/upload_url",
    "file-upload-url-private": "api/v3/private/files/upload_url",
    "asm_notes": "api/v3/asm/notes/{item_type}/{item_id}",
}

AGENT_FINAL_RESPONSE_MESSAGE_TYPE = "AGENT_FINAL_RESPONSE"
AGENT_JSON_ACCEPT_HEADERS = {"Accept": "application/json"}
# The agent can split one answer into several markdown widgets, e.g. around MITRE ATT&CK trees.
AGENT_RESPONSE_TEXT_SEPARATOR = "\n\n"
AGENT_SESSION_ID_HEADER = "X-Session-Id"
AGENT_USER_MESSAGE_TYPE = "USER_MESSAGE"
# Applies to session DELETE requests. Posting a message is synchronous per the GTI API
# documentation, so it has no request timeout and is bounded by the action's script timeout.
AGENT_REQUEST_TIMEOUT_IN_SECONDS = 300
AGENT_CONNECTIVITY_ERROR_MESSAGE = (
    f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server! "
    "Please check the provided credentials."
)
AGENT_DIRECTORY_PATHS_ERROR_MESSAGE = "The following paths are directories, not files: {paths}."
AGENT_EMPTY_FILES_ERROR_MESSAGE = "The following files are empty: {paths}."
AGENT_HTTP_ERROR_MESSAGE = "Error: {status_code} - {details}."
AGENT_MISSING_SESSION_ID_ERROR_MESSAGE = f"{INTEGRATION_DISPLAY_NAME} Agent did not return a session ID."
AGENT_NO_FINAL_RESPONSE_ERROR_MESSAGE = (
    f"{INTEGRATION_DISPLAY_NAME} Agent didn't return a final response for session "
    "{session_id}."
)
AGENT_NO_RESPONSE_TEXT_MESSAGE = (
    f"{INTEGRATION_DISPLAY_NAME} Agent didn't return a text response for session "
    "{session_id}."
)

XTOOL_HEADER_VALUE = "GTI Google SecOps SOAR"
LIMIT_DEFAULT_VALUE = 50
GRAPHS_LIMIT_DEFAULT_VALUE = 10
SORT_FIELD_MAPPING = {
    "Name": "name",
    "Owner": "owner",
    "Creation Date": "creation_date",
    "Last Modified Date": "last_modified_date",
    "Views Count": "views_count",
    "Comments Count": "comments_count",
}
ITEMS_PER_PAGE = 40

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
QUERY_JOIN_PARAMETER = " OR "
EMAIL_ENTITY_TYPE = 101

ALERT_STATUS_MAPPING = {
    "Select One": None,
    "New": "new",
    "Read": "read",
    "Resolved": "closed",
    "Escalated": "escalated",
    "In Progress": "in_progress",
    "No Action Required": "no_action_required",
    "Duplicate": "duplicate",
    "Not Relevant": "not_relevant",
    "Tracked Externally": "tracked_external",
}

COMMENT_ENDPOINTS_MAPPING = {
    EntityTypes.ADDRESS: "add_comment_address",
    EntityTypes.FILEHASH: "add_comment_filehash",
    EntityTypes.URL: "add_comment_url",
    EntityTypes.HOSTNAME: "add_comment_hostname",
    EntityTypes.DOMAIN: "add_comment_domain",
}

CASE_INSENSITIVE_ENTITIES = [
    EntityTypes.ADDRESS,
    EntityTypes.MACADDRESS,
    EntityTypes.CHILDHASH,
    EntityTypes.FILEHASH,
]

VOTE_ENDPOINTS_MAPPING = {
    EntityTypes.ADDRESS: "add_vote_address",
    EntityTypes.FILEHASH: "add_vote_filehash",
    EntityTypes.URL: "add_vote_url",
    EntityTypes.HOSTNAME: "add_vote_hostname",
    EntityTypes.DOMAIN: "add_vote_domain",
}

POSSIBLE_IOC_TYPES = ["IP", "Hash", "URL", "Domain"]

ENTITY_TYPE_MAP = {
    EntityTypes.FILEHASH: "files",
    EntityTypes.CHILDHASH: "files",
    EntityTypes.PARENTHASH: "files",
    EntityTypes.URL: "urls",
    EntityTypes.ADDRESS: "ip_addresses",
    EntityTypes.HOSTNAME: "domains",
    EntityTypes.DOMAIN: "domains",
}

RELATIONSHIP_MAP = {
    "ip_addresses": {
        "Domain": "resolutions",
        "URL": "urls",
        "Hash": "communicating_files",
        "Hash_2": "referrer_files",
    },
    "domains": {
        "IP": "resolutions",
        "Domain": "siblings",
        "URL": "urls",
        "Hash": "communicating_files",
        "Hash_2": "referrer_files",
    },
    "urls": {
        "IP": "contacted_ips",
        "Domain": "contacted_domains",
        "URL": "redirecting_urls",
        "Hash": "communicating_files",
        "Hash_2": "referrer_files",
    },
    "files": {
        "IP": "contacted_ips",
        "IP_2": "embedded_ips",
        "Domain": "contacted_domains",
        "Domain_2": "embedded_domains",
        "URL": "contacted_urls",
        "URL_2": "embedded_urls",
        "Hash": "bundled_files",
        "Hash_2": "execution_parents",
        "Hash_3": "similar_files",
    },
    "collections": {
        "IP": "ip_addresses",
        "Domain": "domains",
        "URL": "urls",
        "Hash": "files",
    },
}

PRIVATE_URL_DATA_TYPE = "private_url"

MAX_SEARCH_ISSUES_LIMIT = 200
MAX_SEARCH_ENTITIES_LIMIT = 200
MAX_IOC_SEARCH_LIMIT = 200
MAX_ASSOCIATIONS_TO_RETURN_DEFAULT_VALUE = 50
MAX_ASSOCIATIONS_TO_RETURN_LIMIT = 1000
MIN_ASSOCIATIONS_TO_RETURN_LIMIT = 1
CUSTOM_TIME = "Custom"
TIME_INTERVALS = {
    "Last Hour": timedelta(hours=1),
    "Last 6 Hours": timedelta(hours=6),
    "Last 24 Hours": timedelta(hours=24),
    "Last Week": timedelta(weeks=1),
    "Last Month": timedelta(weeks=4),
}
ASM_ISSUE_SEVERITY_MAPPING = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "informational": 5,
}
ASM_ISSUE_STATUS_MAPPING = {"Open": "open", "Closed": "closed"}
DEFAULT_PAGE_SIZE = 100

DEFAULT_ISSUE_STATUS_FILTER: str = "open"
ISSUE_STATUS_LIST: list[str] = [DEFAULT_ISSUE_STATUS_FILTER, "closed"]

ISSUE_STATUS_MAPPING = {
    "New": "open_new",
    "Triaged": "open_triaged",
    "In Progress": "open_in_progress",
    "Resolved": "closed_resolved",
    "Duplicate": "closed_duplicate",
    "Out Of Scope": "closed_out_of_scope",
    "Not A Security Issue (Benign)": "closed_benign",
    "Risk Accepted": "closed_risk_accepted",
    "False Positive": "closed_false_positive",
    "Unable To Reproduce": "closed_no_repro",
    "Tracked Externally": "closed_tracked_externally",
    "Mitigated": "closed",
}

CASE_WALL_LINK = "https://www.virustotal.com/gui/{entity_type}/{entity}/detection"
PRIVATE_CASE_WALL_LINK = (
    "https://www.virustotal.com/gui/private-scanning/{entity_type}/{entity}"
)
COLLECTIONS_CASE_WALL_LINK = "https://www.virustotal.com/gui/collection/{ioc}"
DATA_ENRICHMENT_PREFIX = "GTI"
IOC_MAPPING = {
    "files": "file",
    "urls": "url",
    "ip_addresses": "ip-address",
    "domains": "domain",
}
COMPLETED = "completed"

MD5_LENGTH = 32
SHA1_LENGTH = 40
SHA256_LENGTH = 64

# DTM Alerts connector
DTM_ALERTS_CONNECTOR = "Google Threat Intelligence - DTM Alerts Connector"
MAX_LIMIT = 25
SEVERITIES = ["low", "medium", "high"]
STORED_IDS_LIMIT = 10_000
DEFAULT_DEVICE_VENDOR = "Google Threat Intelligence"
DEFAULT_DEVICE_PRODUCT = "DTM Alert"
SEVERITY_MAPPING: dict[str, int] = {
    "informational": -1,
    "low": 40,
    "medium": 60,
    "high": 80,
    "critical": 100,
}
SEVERITY_GTI_MAPPING = {
    "SEVERITY_NONE": -1,
    "SEVERITY_UNKNOWN": -1,
    "SEVERITY_INFO": -1,
    "SEVERITY_LOW": 40,
    "SEVERITY_MEDIUM": 60,
    "SEVERITY_HIGH": 80,
    "SEVERITY_CRITICAL": 100,
}
MAIN_ALERT_EVENT_TYPE = "Main Alert"
ALERT_STATUSES = ["escalated", "in_progress", "new", "read"]
EVENTS_LIMIT = 400
DTM_DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DOC_KEY = "doc"
PASSWORD_MASK_CHAR = "*"
PASSWORD_KEY = "password"
PLAIN_TEXT_KEY = "plain_text"
SERVICE_ACCOUNT_KEY = "service_account"

# GTI Alerts connector
GTI_ALERTS_DEFAULT_LIMIT: int = 25
GTI_ALERTS_MAX_LIMIT: int = 100
GTI_ALERTS_SEVERITIES: list[str] = [
    "Informational",
    "Low",
    "Medium",
    "High",
    "Critical",
]

GTI_ENTITY_IP_KEYS: set[str] = {"ips", "ip", "ip_addresses", "ipaddresses"}
GTI_ENTITY_DOMAIN_KEYS: set[str] = {
    "domains",
    "domain",
    "targetdomains",
    "target_domains",
    "hostnames",
    "hostname",
    "hosts",
}
GTI_ENTITY_USER_KEYS: set[str] = {
    "author",
    "authors",
    "usernames",
    "username",
    "user_name",
    "user_names",
    "users",
    "user",
    "affectedaccounts",
    "affected_accounts",
    "emails",
    "email",
    "identities",
}
GTI_ENTITY_URL_KEYS: set[str] = {
    "urls",
    "url",
    "links",
    "link",
    "sourceuri",
    "source_uris",
}
GTI_ENTITY_HASH_KEYS: set[str] = {"hashes", "hash", "sha256", "md5"}
GTI_ENTITY_FILE_KEYS: set[str] = {"files", "filenames", "filename"}
GTI_ENTITY_CVE_KEYS: set[str] = {
    "cve",
    "cve_id",
    "cve_ids",
    "cveid",
    "cveids",
    "cves",
    "vulnerabilities",
}

GTI_ENTITY_KEY_ALIASES: tuple[tuple[frozenset[str], tuple[str, ...]], ...] = (
    (frozenset(GTI_ENTITY_IP_KEYS), ("ip", "ip_address")),
    (frozenset(GTI_ENTITY_DOMAIN_KEYS), ("domain", "domain_name")),
    (frozenset(GTI_ENTITY_USER_KEYS), ("user", "user_name", "userName", "username", "author")),
    (frozenset(GTI_ENTITY_URL_KEYS), ("url", "sourceUri")),
    (frozenset(GTI_ENTITY_HASH_KEYS), ("hash", "file_hash")),
    (frozenset(GTI_ENTITY_FILE_KEYS), ("filename",)),
    (frozenset(GTI_ENTITY_CVE_KEYS), ("cve", "cve_id", "cveId")),
)
GTI_ALERT_ENTITY_KEYS: set[str] = set().union(*(keys for keys, _ in GTI_ENTITY_KEY_ALIASES))

GTI_ROOT = "https://www.virustotal.com/api/v3/"
MANDIANT_ROOT = "https://api.intelligence.mandiant.com/v4"

# ASM Issues connector
ASM_ISSUES_CONNECTOR_NAME = "Google Threat Intelligence - ASM Issues Connector"
ISSUES_POSSIBLE_SEVERITIES = ["Informational", "Low", "Medium", "High", "Critical"]
DEFAULT_ASM_DEVICE_PRODUCT = "ASM Issues"
GTI_ALERTS_DEFAULT_DEVICE_PRODUCT: str = "GTI Alert"
PRIORITY_MAPPING = {1: 100, 2: 80, 3: 60, 4: 40, 5: -1}
MAX_PAGE_SIZE = 100
ASM_ISSUES_TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"
ASM_ISSUES_MIN_WINDOW_HOURS: int = 1
ASM_ISSUES_INITIAL_WINDOW_HOURS: int = 6
ASM_ISSUES_MAX_WINDOW_HOURS: int = 168
ASM_ISSUES_MAX_WINDOW_PROBES: int = 50
ASM_ISSUES_WINDOW_RESULTS_CEILING: int = 1000
ASM_ISSUES_WINDOW_WALK_TIMEOUT_THRESHOLD: float = 0.5

# Livehunt Connector
LIVEHUNT_CONNECTOR = "Google Threat Intelligence - Livehunt Connector"
DEFAULT_HOURS_BACKWARDS = 1
DEFAULT_NOTIFICATIONS_LIMIT = 40
MAX_NOTIFICATIONS_LIMIT = 40
LIVEHUNT_CONNECTOR_DEFAULT_DEVICE_PRODUCT = "Livehunt"
NOTIFICATION_ALLOWED_VERDICTS = ["VERDICT_MALICIOUS", "VERDICT_SUSPICIOUS"]
SUSPICIOUS_VERDICTS = ["VERDICT_SUSPICIOUS", "VERDICT_MALICIOUS"]

# Widget theme
WIDGET_LIGHT_THEME_COLORS = {
    "theme": "light",
    "fg1": "4f5064",
    "bg1": "ffffff",
    "bg2": "f4f5fa",
    "bd1": "d2d7e9",
}

WIDGET_DARK_THEME_COLORS = {
    "theme": "dark",
    "fg1": "b2b2b8",
    "bg1": "1b1b22",
    "bg2": "1f1f29",
    "bd1": "303045",
}

WIDGET_CHRONICLE_THEME_COLORS = {
    "theme": "dark",
    "fg1": "ffffff",
    "bg1": "212c44",
    "bg2": "3a4a6c",
    "bd1": "5d708a",
}

WIDGET_THEME_MAPPING = {
    "Light": WIDGET_LIGHT_THEME_COLORS,
    "Dark": WIDGET_DARK_THEME_COLORS,
    "Chronicle": WIDGET_CHRONICLE_THEME_COLORS,
}

EXTEND_GRAPH_URL = "{}/external/v1/investigator/ExtendCaseGraph"


class ASMItemType(Enum):
    ISSUE = "issue"
    ENTITY = "entity"


class Order(Enum):
    ASC = "asc"
    DESC = "desc"

from __future__ import annotations
INTEGRATION_NAME = "Siemplify ThreatFuse"
INTEGRATION_IDENTIFIER = "SiemplifyThreatFuse"
VENDOR = "Siemplify"
PRODUCT = "Siemplify ThreatFuse"

ENRICHMENT_PREFIX = "TFuse"

GET_RELATED_ASSOCIATION_SCRIPT_NAME = "Get Related Associations"

ASSOCIATIONS_TYPES = {
    "Observables": "intelligence",
    "Threat Bulletins": "tipreport",
    "Actors": "actor",
    "Attack Patterns": "attackpattern",
    "Campaigns": "campaign",
    "Courses Of Action": "courseofaction",
    "Identities": "identity",
    "Incidents": "incident",
    "Infrastructure": "infrastructure",
    "Intrusion Sets": "intrusionset",
    "Malware": "malware",
    "Signatures": "signature",
    "Tools": "tool",
    "TTPs": "ttp",
    "Vulnerabilities": "vulnerability",
}

VULNERABILITY_ASSOCIATION_TYPE = "vulnerability"
CAMPAIGN_ASSOCIATION_TYPE = "campaign"
ACTOR_ASSOCIATION_TYPE = "actor"
SIGNATURE_ASSOCIATION_TYPE = "signature"
THREAT_BULLETINS_ASSOCIATION_TYPE = "tipreport"
ATTACK_PATTERNS_ASSOCIATION_TYPE = "attackpattern"
COURSES_OF_ACTION_ASSOCIATION_TYPE = "courseofaction"
IDENTITY_ASSOCIATION_TYPE = "identity"
INCIDENT_ASSOCIATION_TYPE = "incident"
INFRASTRUCTURE_ASSOCIATION_TYPE = "infrastructure"
INTRUSION_SET_ASSOCIATION_TYPE = "intrusionset"
MALWARE_ASSOCIATION_TYPE = "malware"
TOOL_ASSOCIATION_TYPE = "tool"
TTP_ASSOCIATION_TYPE = "ttp"

CVE_ENTITY_TYPE = "CVE"
CAMPAIGN_ENTITY_TYPE = "THREATCAMPAIGN"
ACTOR_ENTITY_TYPE = "THREATACTOR"
SIGNATURE_ENTITY_TYPE = "THREATSIGNATURE"

ASSOCIATION_TYPE_TO_ENTITY = {
    VULNERABILITY_ASSOCIATION_TYPE: CVE_ENTITY_TYPE,
    CAMPAIGN_ASSOCIATION_TYPE: CAMPAIGN_ENTITY_TYPE,
    ACTOR_ASSOCIATION_TYPE: ACTOR_ENTITY_TYPE,
    SIGNATURE_ASSOCIATION_TYPE: SIGNATURE_ENTITY_TYPE,
}

SEVERITIES = {
    "Very High": "very-high",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
}

SEVERITIES_ORDER = {"very-high": 4, "high": 3, "medium": 2, "low": 1}

SEVERITIES_TO_SIEMPLIFY_SEVERITIES = {
    "very-high": 100,
    "high": 80,
    "medium": 60,
    "low": 40,
}

SEVERITIES_COLORS = {
    "very-high": "#de2026",
    "high": "#de2026",
    "medium": "#f79420",
    "low": "#12ab50",
}

INDICATOR_STATUSES = {
    "Inactive": "inactive",
    "False Positive": "falsepos",
    "Active": "active",
}

MAX_HASHES_TO_RETURN_DEFAULT = 50
MAX_URLS_TO_RETURN_DEFAULT = 50
MAX_DOMAINS_TO_RETURN_DEFAULT = 50
MAX_EMAIL_ADDRESSES_TO_RETURN_DEFAULT = 50
MAX_IPS_TO_RETURN_DEFAULT = 50
MIN_SCORE_THRESHOLD = 0.0
MAX_SCORE_THRESHOLD = 10.0

MAX_ASSOCIATIONS_TO_RETURN_DEFAULT = 5
MAX_STATICSTICS_TO_RETURN_DEFAULT = 3
MAX_STATICSTICS_TO_FETCH_DEFAULT = 1000
# Later this count should be removed and instead of MAX_STATISTICS_FOR_TTP_TYPE_DEFAULT should be used
# MAX_STATICSTICS_TO_FETCH_DEFAULT as a regular pagination limit. For now Anomali doesn't support statistics results
# more than 75 for TTP type.
MAX_STATISTICS_FOR_TTP_TYPE_DEFAULT = 75

MAX_CONFIDENCE = 100
MIN_CONFIDENCE = 0

OR = "OR"
AND = "AND"
GTE = ">="

MD5_INDICATOR_TYPE = "md5"
URL_INDICATOR_TYPE = "url"
DOMAIN_INDICATOR_TYPE = "domain"
EMAIL_INDICATOR_TYPE = "email"
IP_INDICATOR_TYPE = "ip"

CVSS2 = "CVSS 2.0"
CVSS3 = "CVSS 3.0"

NOT_ASSIGNED = "N/A"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

PAGE_SIZE = 1000

TLP_MAPPINGS = {"Red": "red", "Green": "green", "Amber": "amber", "White": "white"}

CLASSIFICATION_MAPPINGS = {"Private": "private", "Public": "public"}

THREAT_TYPE_MAPPINGS = {
    "APT": "apt",
    "Adware": "adware",
    "Anomalous": "anomalous",
    "Anomyzation": "anonymization",
    "Bot": "bot",
    "Brute": "brute",
    "C2": "c2",
    "Compromised": "compromised",
    "Crypto": "crypto",
    "Data Leakage": "data_leakage",
    "DDOS": "ddos",
    "Dynamic DNS": "dyn_dns",
    "Exfil": "exfil",
    "Exploit": "exploit",
    "Fraud": "fraud",
    "Hacking Tool": "hack_tool",
    "I2P": "i2p",
    "Informational": "informational",
    "Malware": "malware",
    "P2P": "p2p",
    "Parked": "parked",
    "Phish": "phish",
    "Scan": "scan",
    "Sinkhole": "sinkhole",
    "Social": "social",
    "Spam": "spam",
    "Suppress": "suppress",
    "Suspicious": "suspicious",
    "TOR": "tor",
    "VPS": "vps",
}

ANONYMOUS_SUBMISSION_DEFAULT_VALUE = False
OVERRIDE_SYSTEM_CONFIDENCE = False
SELECT_ONE = "Select One"
DEFAULT_OBSERVABLE_SOURCE = "Siemplify"
DEFAULT_THREAT_TYPE = "APT"
DEFAULT_CLASSIFICATION = "Private"

APPROVED_JOB_STATUS = "approved"
JOB_STATUS_WAITING_INTERVAL = 1  # in seconds

VALID_EMAIL_REGEXP = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

GREEN = "#12ab50"
ORANGE = "#f79420"

DEFAULT_INSIGHT_PLACEHOLDER = "---"

IP_INSIGHT_HTML_TEMPLATE = """<div style="display: flex; flex-direction: row; justify-content:space-around; "><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Severity</h5>
<h2 style="text-transform: uppercase; color: {severity_color}">{severity}</h2></div><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Confidence</h5>
<h2 style="text-transform: uppercase; color: {confidence_color}">{confidence}</h2></div></div>
Status: {status}

ASN: {asn}
Country: {country}
VirusTotal Classification: {virus_total_classification}
Domain Tools Classification: {domain_tools_classification}
Google Safe Browsing Classification: {google_safe_browsing_classification}
IPVoid Classification: {ipvoid_classification}
IPVoid Detections: {ipvoid_detections}
Project Honey Pot Classification: {honeypot_classification}
Web of Trust Classification: {web_of_trust_classification}

Type: {itype}
Threat Type: {threat_type}
Source: {source}
More details: <a target="_blank" href="{report_link}">{report_link}</a>
"""

URL_INSIGHT_HTML_TEMPLATE = """<div style="display: flex; flex-direction: row; justify-content:space-around; "><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Severity</h5>
<h2 style="text-transform: uppercase; color: {severity_color}">{severity}</h2></div><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Confidence</h5>
<h2 style="text-transform: uppercase; color: {confidence_color}">{confidence}</h2></div></div>
Status: {status}

IP: {ip}
Country: {country}
Organization: {org}
VirusTotal Classification: {virus_total_classification}
Domain Tools Classification: {domain_tools_classification}
Google Safe Browsing Classification: {google_safe_browsing_classification}
IPVoid Classification: {ipvoid_classification}
IPVoid Detections: {ipvoid_detections}
Project Honey Pot Classification: {honeypot_classification}
Web of Trust Classification: {web_of_trust_classification}

Type: {itype}
Threat Type: {threat_type}
Source: {source}
More details: <a target="_blank" href="{report_link}">{report_link}</a>
"""

DOMAIN_INSIGHT_HTML_TEMPLATE = """<div style="display: flex; flex-direction: row; justify-content:space-around; "><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Severity</h5>
<h2 style="text-transform: uppercase; color: {severity_color}">{severity}</h2></div><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Confidence</h5>
<h2 style="text-transform: uppercase; color: {confidence_color}">{confidence}</h2></div></div>
Status: {status}

IP: {ip}
Country: {country}
Organization: {org}
Domain Registration Address: {registrant_address}
Domain Created: {registration_created}
Domain Last Updated: {registration_updated}
VirusTotal Classification: {virus_total_classification}
Domain Tools Classification: {domain_tools_classification}
Google Safe Browsing Classification: {google_safe_browsing_classification}
IPVoid Classification: {ipvoid_classification}
IPVoid Detections: {ipvoid_detections}
Project Honey Pot Classification: {honeypot_classification}
Web of Trust Classification: {web_of_trust_classification}

Type: {itype}
Threat Type: {threat_type}
Source: {source}
More details: <a target="_blank" href="{report_link}">{report_link}</a>
"""

FILEHASH_INSIGHT_HTML_TEMPLATE = """<div style="display: flex; flex-direction: row; justify-content:space-around; "><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Severity</h5>
<h2 style="text-transform: uppercase; color: {severity_color}">{severity}</h2></div><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Confidence</h5>
<h2 style="text-transform: uppercase; color: {confidence_color}">{confidence}</h2></div></div>
Status: {status}

Type: {itype}
Threat Type: {threat_type}
Source: {source}
More details: <a target="_blank" href="{report_link}">{report_link}</a>
"""

EMAIL_INSIGHT_HTML_TEMPLATE = """<div style="display: flex; flex-direction: row; justify-content:space-around; "><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Severity</h5>
<h2 style="text-transform: uppercase; color: {severity_color}">{severity}</h2></div><div style="display:flex; flex-direction: column; justify-content: center; align-items:center;">
<h5>Confidence</h5>
<h2 style="text-transform: uppercase; color: {confidence_color}">{confidence}</h2></div></div>
Status: {status}

Type: {itype}
Threat Type: {threat_type}
Source: {source}
More details: <a target="_blank" href="{report_link}">{report_link}</a>
"""

MAX_OBSERVABLES_PER_ALERT = 200
DEFAULT_SCRIPT_TIMEOUT = 300
DEFAULT_PRODUCT_FIELD_NAME = "Product Name"
DEFAULT_OBSERVABLE_TYPE_FILTER = "url, domain, email, hash, ip, ipv6"
DEFAULT_OBSERVABLE_STATUS = "active"

OBSERVABLE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

OBSERVABLE_TYPES = ["url", "domain", "email", "hash", "ip", "ipv6"]
OBSERVABLE_STATUSES = ["active", "inactive", "falsepos"]
DEFAULT_LOWEST_SEVERITY_TO_FETCH = "High"
DEFAULT_MAX_DAYS_BACKWARDS = 1

API_UNAUTHORIZED_ERROR = 401
API_NOT_FOUND_ERROR = 404
API_BAD_REQUEST = 400

RULE_GENERATOR = f"{INTEGRATION_NAME} Observables Ingestion"
ALERT_NAME_WITHOUT_SOURCE_GROUPING = f"New {INTEGRATION_NAME} Observables"
DEFAULT_LOWEST_CONFIDENCE_TO_FETCH = 50

WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"

SEVERITIES_MAP = {
    "Low": ["low", "medium", "high", "very-high"],
    "Medium": ["medium", "high", "very-high"],
    "High": ["high", "very-high"],
    "Very-High": ["very-high"],
}

MAX_IDS_IN_IDS_FILE = 5000
IDS_FILE = "ids.json"
TIMEOUT_THRESHOLD = 0.9

MAX_DESCRIPTION_LENGTH = (
    150  # The max length of a association's description, splitted with spaces
)
MAX_BODY_LENGTH = 150  # the max length of association's body, splitted with spaces

SPACE_CHARACTER = " "

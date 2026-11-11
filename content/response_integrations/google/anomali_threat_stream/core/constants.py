from __future__ import annotations
INTEGRATION_NAME = "Anomali ThreatStream"
INTEGRATION_IDENTIFIER = "AnomaliThreatStream"

# ACTIONS NAMES
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich Entities"
ADD_TAGS_TO_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Add Tags To Entities"
REMOVE_TAGS_FROM_ENTITIES_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Remove Tags From Entities"
)
REPORT_AS_FALSE_POSITIVE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Report As False Positive"
SUBMIT_OBSERVABLES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Submit Observables"
GET_RELATED_ASSOCIATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Related Associations"
GET_RELATED_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Related Entities"

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
EMAIL_TYPE = 101

VULNERABILITY_ASSOCIATION_TYPE = "vulnerability"
CAMPAIGN_ASSOCIATION_TYPE = "campaign"
ACTOR_ASSOCIATION_TYPE = "actor"
SIGNATURE_ASSOCIATION_TYPE = "signature"

CVE_ENTITY_TYPE = "CVE"
CAMPAIGN_ENTITY_TYPE = "THREATCAMPAIGN"
ACTOR_ENTITY_TYPE = "THREATACTOR"
SIGNATURE_ENTITY_TYPE = "THREATSIGNATURE"

ENTITY_CREATING_VALID_VALUES_MAPPER = [
    VULNERABILITY_ASSOCIATION_TYPE,
    CAMPAIGN_ASSOCIATION_TYPE,
    ACTOR_ASSOCIATION_TYPE,
    SIGNATURE_ASSOCIATION_TYPE,
]

ASSOCIATION_TYPE_TO_ENTITY = {
    VULNERABILITY_ASSOCIATION_TYPE: CVE_ENTITY_TYPE,
    CAMPAIGN_ASSOCIATION_TYPE: CAMPAIGN_ENTITY_TYPE,
    ACTOR_ASSOCIATION_TYPE: ACTOR_ENTITY_TYPE,
    SIGNATURE_ASSOCIATION_TYPE: SIGNATURE_ENTITY_TYPE,
}
# The max length of a association's description, splitted with spaces
MAX_LENGTH_FOR_JSON_RESULT_STRING = 150
MAX_ASSOCIATIONS_TO_RETURN_DEFAULT = 5
MAX_STATISTICS_TO_RETURN_DEFAULT = 3
MAX_ENTITIES_TO_RETURN_DEFAULT = 50

ENRICHMENT_PREFIX = "AnomaliTS"
MAX_CONFIDENCE = 100
MIN_CONFIDENCE = 0
JOB_STATUS_WAITING_INTERVAL = 1

API_NOT_FOUND_ERROR = 404
API_UNAUTHORIZED_ERROR = 401
API_BAD_REQUEST = 400

APPROVED_JOB_STATUS = "approved"
NOT_ASSIGNED = "N/A"
SPACE_CHARACTER = " "
SEVERITIES = {
    "Very High": "very-high",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
}

SEVERITIES_ORDER = {"very-high": 4, "high": 3, "medium": 2, "low": 1}

INDICATOR_STATUSES = {
    "Inactive": "inactive",
    "False Positive": "falsepos",
    "Active": "active",
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

GREEN = "#12ab50"
ORANGE = "#f79420"

MD5_INDICATOR_TYPE = "md5"
URL_INDICATOR_TYPE = "url"
DOMAIN_INDICATOR_TYPE = "domain"
EMAIL_INDICATOR_TYPE = "email"
IP_INDICATOR_TYPE = "ip"
DEFAULT_INSIGHT_PLACEHOLDER = "---"

OR = "OR"
AND = "AND"
GTE = ">="

OBSERVABLE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DEFAULT_CLASSIFICATION = "Private"
DEFAULT_THREAT_TYPE = "APT"
DEFAULT_OBSERVABLE_SOURCE = "Siemplify"
SELECT_ONE = "Select One"


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

ENDPOINTS_MAPPER = {
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

CLASSNAME_MAPPER = {
    "Threat Bulletins": "ThreatBulletinsDetails",
    "Actors": "ActorDetails",
    "Attack Patterns": "AttackPatternDetails",
    "Campaigns": "CampaignDetails",
    "Courses Of Action": "CourseOfActionDetails",
    "Identities": "IdentityDetails",
    "Incidents": "IncidentDetails",
    "Infrastructure": "InfrastructureDetails",
    "Intrusion Sets": "IntrusionSetDetails",
    "Malware": "MalwareDetails",
    "Signatures": "SignatureDetails",
    "Tools": "ToolDetails",
    "TTPs": "TTPDetails",
    "Vulnerabilities": "Vulnerability",
}

PARSER_MAPPER = {
    ENDPOINTS_MAPPER["Threat Bulletins"]: "build_threat_bulletins_details_obj",
    ENDPOINTS_MAPPER["Actors"]: "build_actor_details_obj",
    ENDPOINTS_MAPPER["Attack Patterns"]: "build_attackpattern_details_obj",
    ENDPOINTS_MAPPER["Campaigns"]: "build_campaign_details_obj",
    ENDPOINTS_MAPPER["Courses Of Action"]: "build_course_of_action_details_obj",
    ENDPOINTS_MAPPER["Identities"]: "build_identity_details_obj",
    ENDPOINTS_MAPPER["Incidents"]: "build_incident_details_obj",
    ENDPOINTS_MAPPER["Infrastructure"]: "build_infrastructure_details_obj",
    ENDPOINTS_MAPPER["Intrusion Sets"]: "build_intrusionset_details_obj",
    ENDPOINTS_MAPPER["Malware"]: "build_malware_details_obj",
    ENDPOINTS_MAPPER["Signatures"]: "build_signature_details_obj",
    ENDPOINTS_MAPPER["Tools"]: "build_tool_details_obj",
    ENDPOINTS_MAPPER["TTPs"]: "build_ttp_details_obj",
    ENDPOINTS_MAPPER["Vulnerabilities"]: "build_vulnerability_obj",
}

MAX_DESCRIPTION_LENGTH = 150
MAX_BODY_LENGTH = 150
MAX_STATICSTICS_TO_FETCH_DEFAULT = 1000
# Later this count should be removed and instead of MAX_STATISTICS_FOR_TTP_TYPE_DEFAULT should be used
# MAX_STATICSTICS_TO_FETCH_DEFAULT as a regular pagination limit. For now Anomali doesn't support statistics results
# more than 75 for TTP type.
MAX_STATISTICS_FOR_TTP_TYPE_DEFAULT = 75

ENTITY_TYPES = {
    MD5_INDICATOR_TYPE: "all_hashes",
    URL_INDICATOR_TYPE: "urls",
    IP_INDICATOR_TYPE: "ips",
    DOMAIN_INDICATOR_TYPE: "domains",
    EMAIL_INDICATOR_TYPE: "emails",
}

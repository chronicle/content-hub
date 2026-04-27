from __future__ import annotations
INTEGRATION_NAME = "BlueLiv"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
ADD_COMMENT_TO_THREAT_ACTION = f"{INTEGRATION_NAME} - Add Comment To Threat"
MARK_THREAT_AS_FAVORITE = f"{INTEGRATION_NAME} - Mark Threat As Favorite"
ADD_LABELS_TO_THREATS = f"{INTEGRATION_NAME} - Add Labels to Threats"
REMOVE_LABELS_FROM_THREATS = f"{INTEGRATION_NAME} - Remove Labels From Threats"
ENRICH_ENTITIES = f"{INTEGRATION_NAME} - Enrich Entities"
LIST_ENTITY_THREATS = f"{INTEGRATION_NAME} - List Entity Threats"

AUTH_QUERY = "{}/api/v2/auth"
PING_URL = "{}/api/v2/organization/{}/module/0/resource?page=1&maxRows=1"
ADD_COMMENT_TO_THREAT_URL = "{}/api/v2/organization/{}/module/{}/{}/resource/{}/comment"
MARK_THREAT_AS_FAVORITE_URL = "{}/api/v2/organization/{}/module/{}/{}/resource/fav"
GET_LABELS_URL = "{}/api/v2/label/organization/{}"
GET_THREAT_URL = "{}/api/v2/organization/{}/module/{}/{}/resource/{}"
ADD_LABELS_TO_THREATS_URL = "{}/api/v2/organization/{}/module/{}/{}/resource/label"
REMOVE_LABELS_TO_THREATS_URL = "{}/api/v2/organization/{}/module/{}/{}/resource/label"
GET_THREATS_BY_FILTERS_URL = "{}/api/v2/organization/{}/module/{}/resource"
GET_THREAT_EXTRADATA_URL = (
    "{}/api/v2/organization/{}/module/{}/{}/resource/{}/extradata_info"
)
GET_BLUELIV_DETAILS_URL = "{}/api/v2/organization/{}/module"
GET_ENTITY_DETAILS = "{}/api/v2/organization/{}/module/0/resource?notcache=1629972711683&page=1&maxRows=100&q={}&read=0&analysisCalcResult=INFORMATIVE,NEGATIVE,POSITIVE"

ENRICH_IP_URL = "{}/api/v1/ip/{}"
ENRICH_HASH_URL = "{}/api/v1/malware/{}"
ENRICH_CVE_URL = "{}/api/v1/cve/{}"
GET_URL_DETAILS_URL = "{}/api/v1/indicator/"
ENRICH_URL_URL = "{}/api/v1/crime-server/{}"
GET_THREAT_CAMPAIGN_DETAILS_URL = "{}/api/v1/campaign/"
ENRICH_CAMPAIGN_URL = "{}/api/v1/campaign/{}"
GET_THREAT_ACTOR_DETAILS_URL = "{}/api/v1/threat-actor/"
ENRICH_ACTOR_URL = "{}/api/v1/threat-actor/{}"
GET_THREAT_SIGNATURE_DETAILS_URL = "{}/api/v1/signature/"
ENRICH_SIGNATURE_URL = "{}/api/v1/signature/{}"

CUSTOM_LINK_URL = "{}/dashboard/organizations/{}/modules/{}/threat_context/{}/"

FAVORITE_STATUS = {
    "Not Starred": "NOT_STARRED",
    "User Starred": "USER_STARRED",
    "Group Starred": "GROUP_STARRED",
    "Full Starred": "FULL_STARRED",
}

# CONNECTORS
DEVICE_VENDOR = "BlueLiv"
THREATS_CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_NAME} - Threats Connector"
IDS_FILE = "ids.json"
MAP_FILE = "map.json"
ALERT_ID_FIELD = "id"
LIMIT_IDS_IN_IDS_FILE = 1000
TIMEOUT_THRESHOLD = 0.9
WHITELIST_FILTER = "whitelist"
BLACKLIST_FILTER = "blacklist"
ORDER_BY_STRING = "D,ASC"
DEFAULT_RESULTS_LIMIT = 10
MAX_RESULTS_LIMIT = 100

READING_STATUS_MAPPING = {"Only Read": 1, "Only Unread": 2}

RELATED_INCIDENTS_MAPPING = {"Only Incidents": True, "Only Non Incidents": False}

SEVERITY_TO_SIEM_MAPPING = {"Low": 40, "Medium": 60, "High": 80, "Critical": 100}

# MODULE_TYPES
HACKTIVISM = "HACKTIVISM"
DATA_LEAKAGE = "DATA_LEAKAGE"
CREDENTIALS = "CREDENTIALS"
DARK_WEB = "DARK_WEB"
DOMAIN_PROTECTION = "DOMAIN_PROTECTION"
MALWARE = "MALWARE"
MEDIA_TRACKER = "MEDIA_TRACKER"
MOBILE_APPS = "MOBILE_APPS"
SOCIAL_MEDIA = "SOCIAL_MEDIA"
CREDIT_CARDS_FULL = "CREDIT_CARDS_FULL"
CUSTOM_MODULE = "CUSTOM"
CREDIT_CARD = "credit_card"

ENRICHMENT_PREFIX = "Blueliv"

GREEN_COLOR = "#339966"
RED_COLOR = "#ff0000"
YELLOW_COLOR = "#ffcc00"

MD5_LENGTH = 32
SHA1_LENGTH = 40
SHA256_LENGTH = 64
SHA512_LENGTH = 128

THREAT_CONTEXT = "THREAT_CONTEXT"
MAX_LOWEST_SCORE = 10

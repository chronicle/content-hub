from __future__ import annotations

INTEGRATION_NAME = "Team Cymru Scout"

# Action Names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
ACCOUNT_USAGE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Account Usage"
GET_IP_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get IP Details"
GET_COMMS_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Communications Info"
GET_FINGERPRINTS_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Fingerprints Info"
GET_PDNS_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get PDNS Info"
GET_PORTS_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Ports Info"
GET_PROTO_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Proto Info"
GET_WHOIS_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Whois Info"
GET_X509_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get X509 Info"
ENRICH_IPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Enrich IPs"
SCOUT_SEARCH_SCRIPT_NAME = f"{INTEGRATION_NAME} - Advanced Query"
LIST_IPS_SCRIPT_NAME = f"{INTEGRATION_NAME} - List IP Summary"
EXTRACT_TAGS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Extract Tags"

# Endpoints
BASE_URL = "https://scout.cymru.com/api/scout"
ACCOUNT_USAGE_ENDPOINT = "/usage"
IP_DETAILS_ENDPOINT = "/ip/{}/details"

SCOUT_SEARCH_ENDPOINT = "/search"
LIST_IPS_ENDPOINT = "/ip/foundation"

# Common Messages
INCORRECT_IP_INPUTS = (
    "From the total {} IPs input, following {} IP(s) were found to be "
)
SKIPPING_MSG = "Hence, skipping them from the API input."
ALREADY_ENRICHED_MSG = (
    "Entity: {} has already been enriched by "
    + INTEGRATION_NAME
    + " in the last 24 hrs. Hence, skipping."
)


# Validations
MAX_START_DATE_DAYS = 90
MAX_END_TO_START_DIFF_DAYS = 30
MIN_DAYS = 1
MAX_DAYS = 30
MIN_SIZE = 1
MAX_PAGE_SIZE = {"SCOUT_SEARCH": 5000, "IP_DETAILS": 1000}
BATCH_SIZE = 10

# Errors
ERRORS = {
    "API": {
        "INVALID_API_KEY": "401 - Authentication Error - Invalid API Key found.",
        "EMPTY_API_KEY": "Please provide the API key.",
        "INVALID_UNAME_PASS": "401 - Authentication Error - Invalid username/password combination found.",
        "EMPTY_UNAME_PASS": "Please provide the username/password.",
        "RETRY": "{} - Too many requests, please try again later.",
        "MAX_RETRIES": "Max Retries Error - Request attempts with {} retries failed. {}",
    },
    "VALIDATIONS": {
        "INVALID_IP": "Invalid IP address: {} found. Please re-check the entered IP Address.",
        "INVALID_DATE": "Invalid {}: {} provided. Make sure to enter the date in the format: YYYY-MM-DD.",
        "START_GREATER_THAN_END": "Please provide the start date less than the end date.",
        "END_MUST_NOT_BE_FUTURE": "Please provide the end date less than current time.",
        "MAX_START_DATE": f"Please provide the start date under {MAX_START_DATE_DAYS} days.",
        "MAX_END_START_DIFF": f"Make sure that date difference between end date and start date "
        f"must be less than {MAX_END_TO_START_DIFF_DAYS} days.",
        "INVALID_DAYS": "{} is invalid value for days. Value of 'days' should be between {} and {}.",
        "INVALID_SIZE": "{} is invalid value for size. Value of 'size' should be between {} and {}.",
        "NO_VALID_IPS": "No valid IP addresses were provided.",
        "EXTRA_IPS": "A total of {} valid IPs were provided, breaching the max_ips limit of {}. As a result, the"
        + " following {} additional IPs were skipped: {}",
        "INVALID_IPS_MSG": INCORRECT_IP_INPUTS
        + "of invalid format: {}. "
        + SKIPPING_MSG,
        "NOT_VALID_INTEGERS": "Value of 'days' and 'size' inputs must be a valid integer.",
        "NO_IPS_RESPONSE": "No indicators found for given query and filters.",
        "DUPLICATE_IPS_MSG": INCORRECT_IP_INPUTS + "duplicate: {}. " + SKIPPING_MSG,
    },
}

# Others
DATE_FORMAT = "%Y-%m-%d"
MAX_RETRY_COUNT = 1
BACKOFF_FACTOR = 15
DELIMITER = " | "
SECTION_TO_TABLE_MAPPING = {
    "pdns": ("PDNS", "_pdns_table"),
    "comms": ("Peers", "_peers_table"),
    "open_ports": ("Open Ports", "_open_ports_table"),
    "fingerprints": ("Fingerprints", "_fingerprints_table"),
    "x509": ("Certificates", "_certificates_table"),
    "whois": ("Whois", "_whois_table"),
    "proto_by_ip": ("Proto By IP", "_proto_by_ip_table"),
}

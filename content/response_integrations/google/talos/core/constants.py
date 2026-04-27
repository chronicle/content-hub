from __future__ import annotations
INTEGRATION_NAME = "Talos"
INTEGRATION_DISPLAY_NAME = "Talos ThreatSource"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
WHOIS_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Whois"
GET_REPUTATION_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Get Reputation"


HEADERS = {
    "Host": "talosintelligence.com",
    "Referer": "https://www.talosintelligence.com/reputation_center/lookup",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}

API_ROOT = "https://www.talosintelligence.com"
PING_TEST_DOMAIN = "google.com"
ENDPOINTS = {
    "ping": f"/cloud_intel/whois?whois_query={PING_TEST_DOMAIN}",
    "get_whois_information": "/cloud_intel/whois",
    "get_ip_reputation": "/cloud_intel/ip_reputation",
    "get_domain_reputation": "/cloud_intel/domain_info",
    "get_hostname_reputation": "/cloud_intel/host_info",
    "get_category_info": "cloud_intel/sds_lookup",
    "get_blocked_info": "cloud_intel/talos_blocklist_lookup",
    "get_url_reputation": "/cloud_intel/url_reputation",
}


QUERY_TYPE_MAPPING = {"ip": "ipaddr", "domain": "domain"}

CATEGORY_QUERY_TYPE_MAPPING = {"ip": "ip", "domain": "url"}

REPUTATION_TYPE_MAPPING = {"ip": "ip", "domain": "domain", "hostname": "hostname"}

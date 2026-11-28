from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


# Integration Identifiers
INTEGRATION_IDENTIFIER: str = "DarkEye"
INTEGRATION_DISPLAY_NAME: str = "DarkEye"

# Script Identifiers
PING_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Enrich Entities"

# Configuration Parameters
HAVEIBEENRANSOM_KEY_PARAM: str = "HaveIBeenRansom API Key"
BREACH_HOUSE_KEY_PARAM: str = "Breach House API Key"
VERIFY_SSL_PARAM: str = "Verify SSL"
DEFAULT_VERIFY_SSL: bool = True

# Products
HAVEIBEENRANSOM: str = "HaveIBeenRansom"
HAVEIBEENRANSOM_API_ROOT: str = "https://haveibeenransom.com"
BREACH_HOUSE: str = "Breach House"
BREACH_HOUSE_API_ROOT: str = "https://breach.house"

# leak_type values of the HaveIBeenRansom metadata search and the category each record gets.
# Any other or missing leak_type is a plain "leak".
HAVEIBEENRANSOM_CATEGORIES: Mapping[str, str] = {
    "ransomware_leak": "ransomware",
    "traditional_breach": "breach",
}
HAVEIBEENRANSOM_DEFAULT_CATEGORY: str = "leak"

# Sections of the Breach House search and the category each record gets.
BREACH_HOUSE_CATEGORIES: Mapping[str, str] = {
    "ransomware": "ransomware",
    "breaches": "breach",
    "leads": "leads",
    "stealers": "stealer",
}

# API Constants
ENDPOINTS: Mapping[str, str] = {
    "haveibeenransom-search": "/api/metadata/{field}/{term}",
    "haveibeenransom-search-page": "/api/metadata/{field}/{term}/{page}",
    "breach-house-search": "/api/v1/search",
    "breach-house-me": "/api/v1/me",
}
# HaveIBeenRansom has no account endpoint, so Ping runs one domain search.
PING_DOMAIN: str = "example.com"
USER_AGENT: str = "Google-SecOps-DarkEye"
REQUEST_TIMEOUT: int = 30

# Action Parameters
MAX_PAGES_PARAM: str = "Max Pages"
LIMIT_PARAM: str = "Limit"
MAX_RECORDS_PARAM: str = "Max Records"
DEFAULT_MAX_PAGES: int = 5
MAX_PAGES_LIMIT: int = 20
DEFAULT_LIMIT: int = 25
BREACH_HOUSE_MAX_LIMIT: int = 200
DEFAULT_MAX_RECORDS: int = 100
MAX_RECORDS_LIMIT: int = 500

# Enrichment
ENRICHMENT_PREFIX: str = "DarkEye_"
RECORD_TABLE_HEADERS: tuple[str, ...] = (
    "Product",
    "Category",
    "Title",
    "Website",
    "Group",
    "Country",
    "Discovered",
    "ID",
)

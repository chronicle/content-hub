from __future__ import annotations
GET_ASSETS_URL = "{api_root}/api/3/assets"
GET_ASSET_VULNERABILITIES = "{api_root}/api/3/assets/{asset_id}/vulnerabilities"
GET_VULNERABILITY_DETAILS = "{api_root}/api/3/vulnerabilities/{vulnerability_id}"

# Connector
CONNECTOR_NAME = "Rapid7 InsightVm - Vulnerabilities Connector"
DEFAULT_ASSET_LIMIT = 5
HOST_GROUPING = "Host"
NONE_GROUPING = "None"
DEVICE_VENDOR = "Rapid7"
DEVICE_PRODUCT = "Rapid7 InsightVm"
POSSIBLE_GROUPINGS = [NONE_GROUPING, HOST_GROUPING]
RULE_GENERATOR = "Rapid7 InsightVm Vulnerability"
STORED_IDS_LIMIT = 2000

SEVERITY_MAP = {"Moderate": 60, "Severe": 80, "Critical": 100}

SEVERITIES = ["moderate", "severe", "critical"]

from __future__ import annotations
INTEGRATION_NAME = "HarmonyMobile"
INTEGRATION_DISPLAY_NAME = "Harmony Mobile"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
ENRICH_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Enrich Entities"

ENDPOINTS = {
    "auth": "/auth/external",
    "ping": "/app/SBM/external_api/v1/device_status/?limit=1&offset=0",
    "alerts": "/app/SBM/external_api/v3/alert",
    "devices": "/app/SBM/external_api/v1/device_status",
}

PARAMETERS_DEFAULT_DELIMITER = ","
ENRICHMENT_PREFIX = "HarmonyMobile"

DEVICE_RISK_MAP = {"0": "No Risk", "1": "Low", "2": "Medium", "3": "High"}

DEVICE_RISK_COLOR_MAP = {
    "No Risk": "#339966",
    "Low": "#ffff00",
    "Medium": "#ff9900",
    "High": "#ff0000",
}

DEVICE_STATUS_MAP = {
    "-1": "Processing",
    "0": "Provisioned",
    "1": "Active",
    "4": "Inactive",
}

# Connector
CONNECTOR_NAME = "Harmony Mobile - Alerts Connector"
DEFAULT_TIME_FRAME = 1
DEFAULT_LIMIT = 100
DEVICE_VENDOR = "Checkpoint"
DEVICE_PRODUCT = "Harmony Mobile"


SEVERITY_MAP = {"NONE": -1, "LOW": 40, "MEDIUM": 60, "HIGH": 80}

RISK_MAP = {"NONE": "informational", "LOW": "low", "MEDIUM": "medium", "HIGH": "high"}

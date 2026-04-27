from __future__ import annotations
PROVIDER_NAME = "Cylance"

# Actions
GET_THREAT_DOWNLOAD_LINK = f"{PROVIDER_NAME} - Get Threat Download Link"

ENDPOINTS = {"get_threat_download_link": "/threats/v2/download/{hash}"}
PARAMETERS_DEFAULT_DELIMITER = ","
ENRICH_PREFIX = "Cylance"

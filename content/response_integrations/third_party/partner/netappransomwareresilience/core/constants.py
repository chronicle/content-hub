# Define integration constants here

from __future__ import annotations

# Environment Configuration
OAUTH_URL = "https://staging-netapp-cloud-account.auth0.com/oauth/token"
RRS_SERVICE_URL = "https://k8s-istioing-istioing-4ff0b93b67-74a65bde8c3bb0e5.elb.us-east-1.amazonaws.com/bavinash/v1/account"

# OAuth Configuration
OAUTH_CONFIG = {
    "ENDPOINT": OAUTH_URL,
    "GRANT_TYPE": "client_credentials",
    "AUDIENCE": "https://api.cloud.netapp.com",
    "METHOD": "POST",
    "CONTENT_TYPE": "application/x-www-form-urlencoded",
}

# OAuth Token Constants
EXPIRES_IN_KEY = "expires_in"
TOKEN_EXPIRY_BUFFER_SECONDS = 30  # 30 seconds buffer
DEFAULT_EXPIRY_SECONDS = 1800 - TOKEN_EXPIRY_BUFFER_SECONDS  # 30 minutes

# API Endpoints
ENDPOINT_ENRICH_IP = "enrich/ip-address"
ENDPOINT_ENRICH_STORAGE = "enrich/storage"
ENDPOINT_VOLUME_OFFLINE = "storage/take-volume-offline"
ENDPOINT_TAKE_SNAPSHOT = "storage/take-snapshot"
ENDPOINT_JOB_STATUS = "job/status"
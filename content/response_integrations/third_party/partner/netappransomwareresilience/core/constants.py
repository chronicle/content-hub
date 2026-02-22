# Define integration constants here

from __future__ import annotations
INTEGRATION_NAME = "NetApp Ransomware Resilience"

INTEGRATION_VERSION = "1.0.0"


# Environment Configuration
"""
    Production Environment Configuration:
        OAUTH_URL = "https://netapp-cloud-account.auth0.com/oauth/token"
        RRS_SERVICE_URL = "https://api.bluexp.netapp.com/v1/services/rps/v1/account"
        SSL_VERIFY = True  # Set to True for production environment

    Staging Environment Configuration:
        OAUTH_URL = "https://staging-netapp-cloud-account.auth0.com/oauth/token"
        RRS_SERVICE_URL = "https://k8s-istioing-istioing-4ff0b93b67-74a65bde8c3bb0e5.elb.us-east-1.amazonaws.com/bavinash/v1/account" or "https://staging.api.bluexp.netapp.com/v1/services/rps/v1/account"
        SSL_VERIFY = False  # Set to False to allow self-signed certificates (dev/staging only)

"""
OAUTH_URL = "https://staging-netapp-cloud-account.auth0.com/oauth/token"
RRS_SERVICE_URL = "https://k8s-istioing-istioing-4ff0b93b67-74a65bde8c3bb0e5.elb.us-east-1.amazonaws.com/bavinash/v1/account"
SSL_VERIFY = False  # Set to True for production environment

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
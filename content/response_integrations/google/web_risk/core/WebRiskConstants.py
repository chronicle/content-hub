from __future__ import annotations
INTEGRATION_IDENTIFIER = "WebRisk"

# Actions
PING_SCRIPT_NAME = "Ping"
ENRICH_ENTITIES_SCRIPT_NAME = "EnrichEntities"
SUBMIT_ENTITIES_SCRIPT_NAME = "SubmitEntities"

GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
OAUTH_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

CONFIDENCE_LEVELS = {
    "Select One": None,
    "Low": "LOW",
    "Medium": "MEDIUM",
    "High": "HIGH"
}
PLATFORMS = {
    "Select One": None,
    "Android": "ANDROID",
    "iOS": "IOS",
    "MacOS": "MACOS",
    "Windows": "WINDOWS",
}

# Test uri for enrichment taken from official doc page
# https://cloud.google.com/web-risk/docs/lookup-api#example-urissearch
URI_EXAMPLE = "http://testsafebrowsing.appspot.com/s/malware.html"
from __future__ import annotations


class Config(object):
    # Set application name
    PROVIDER_NAME = "Group-IB DRP"

    # Set up product metadata
    PRODUCT_TYPE = "SOAR"
    PRODUCT_NAME = "Google_Chronicle"
    PRODUCT_VERSION = "unknown"
    INTEGRATION = "Group-IB_DRP_Chronicle"
    INTEGRATION_VERSION = "2.0.0"

    # Set up Google Chronicle variables
    # - Alert
    GC_ALERT_VENDOR = "Group-IB"
    GC_ALERT_PRODUCT = "Group-IB"
    GC_ALERT_NAME_DEFAULT = "Violation URL"
    GC_ALERT_TYPE_DEFAULT = "Violations"
    # - Ping
    GC_PING = "Ping"
    # - Connector to create an Alert
    GC_CONNECTOR_SCRIPT_NAME = "DRP Violations Connector"
    GC_REVIEW_CONNECTOR_SCRIPT_NAME = "DRP Violations Review Connector"
    GC_TYPOSQUATTING_CONNECTOR_SCRIPT_NAME = "DRP Typosquatting Connector"
    # - Fill in the Alert with phishing URLs (API)
    GC_ADD_URLS_SCRIPT_NAME = "Add-Phishing-URLs"
    # - Approve/Reject phishing URL (API)
    GC_APPROVE_SCRIPT_NAME = "URL-Approve"
    GC_REJECT_SCRIPT_NAME = "URL-Reject"
    # - Search
    GC_SEARCH_SCRIPT_NAME = "Get-DRP-Search-Info"

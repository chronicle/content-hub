from __future__ import annotations


class Config:
    # Set application name
    PROVIDER_NAME = "Group-IB TI"

    # Set up product metadata
    PRODUCT_TYPE = "SOAR"
    PRODUCT_NAME = "Google_Chronicle"
    PRODUCT_VERSION = "unknown"
    INTEGRATION = "Group-IB_TI_Chronicle"
    INTEGRATION_VERSION = "1.0.1"

    # Set up Google Chronicle variables
    # - Alert
    GC_ALERT_VENDOR = "Group-IB"
    GC_ALERT_PRODUCT = "Group-IB"
    GC_ALERT_NAME_DEFAULT = "IoC IPs"
    GC_ALERT_TYPE_DEFAULT = "IoC"
    # - Ping
    GC_PING = "Ping"
    # - Connector to create an Alert
    GC_IP_CONNECTOR_SCRIPT_NAME = "TI IoC IP Connector"
    GC_HASH_CONNECTOR_SCRIPT_NAME = "TI IoC Hash Connector"
    # - Fill in the Alert with IoC IPs (API)
    GC_ADD_IP_SCRIPT_NAME = "Add-IoCs-IP"
    # - Updated API
    GC_COLLECTION_SCRIPT_NAME = "Get-Collection-Info"
    # - Graph API
    GC_GRAPH_SCRIPT_NAME = "Get-Graph-Info"
    # - Search API
    GC_SEARCH_SCRIPT_NAME = "Get-TI-Search-Info"
    GC_SEARCH_BY_COLLECTION_SCRIPT_NAME = "Get-TI-Search-Info-By-Collection"

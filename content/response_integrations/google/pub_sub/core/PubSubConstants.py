from __future__ import annotations
INTEGRATION_IDENTIFIER = "PubSub"
INTEGRATION_DISPLAY_NAME = "Pub/Sub"

PING_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Ping"

PUB_SUB_CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Messages Connector"

PUB_SUB_PULL_TIMEOUT = 45
DEFAULT_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform"
]
CONNECTOR_SUB_NAME_FORMAT = "soar_pub_sub_connector_{identifier}_sub"
CONNECTOR_DISPLAY_ID_TEMPLATE = (
    "Pub/Sub_{alert_id}_{connector_identifier}"
)
VENDOR = "Pub/Sub"
PRODUCT = "Message"
ALERT_NAME = "{connector_name} - Alert"
RULE_GENERATOR = "{connector_name} - Rule Generator"
RESERVED_KEYWORD_MAPPING = {
    "pubsub_message_id": "message_messageId",
}

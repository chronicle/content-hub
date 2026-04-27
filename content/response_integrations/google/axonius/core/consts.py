from __future__ import annotations
INTEGRATION_IDENTIFIER = "Axonius"

# Action script names
PING_SCRIPT_NAME = "Ping"
ENRICH_ENTITIES_SCRIPT_NAME = "Enrich Entities"
ADD_TAGS_SCRIPT_NAME = "Add Tags"
REMOVE_TAGS_SCRIPT_NAME = "Remove Tags"
ADD_NOTE_SCRIPT_NAME = "Add Note"

LOGICAL_OR = "or"
AXONIUS_ENRICHMENT_PREFIX = "AXS"
DEFAULT_MAX_NOTES_TO_RETURN = 50
MIN_NOTES_TO_RETURN = 0
NOT_ASSIGNED = "N/A"
USER_INSIGHT_TEMPLATE = """
<p style="margin-bottom: -10px;font-size:15px"><strong>User: {entity_identifier}</strong></p>
<b>Display Name:</b> {display_name}
<b>Username:</b> {username}
<b>Mail:</b> {mail}
<b>Telephone:</b> {user_telephone_number}
<b>Admin:</b> {is_admin}
<b>Local:</b> {is_local}
<b>Locked:</b> {is_locked}
<b>Disabled:</b> {account_disabled}
<b>Link:</b> {html_report_link}
"""
DEVICE_INSIGHT_TEMPLATE = """
<p style="margin-bottom: -10px;font-size:15px"><strong>Endpoint: {entity_identifier}</strong></p>
<b>Asset Name:</b> {asset_name}
<b>Hostname:</b> {hostname}
<b>IP Address:</b> {ip_addresses}
<b>Managed By:</b> {device_managed_by}
<b>OS:</b> {os}
<b>Disabled:</b> {device_disabled}
<b>Link:</b> {html_report_link}
"""
ENDPOINTS_INSIGHT_TITLE = "Endpoint Information"
USERS_INSIGHT_TITLE = "User Information"

HTML_LINK = """<a href="{link}" target="_blank">{link}</a>"""
VALID_EMAIL_REGEXP = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

# API
AUTHORIZATION_ERROR_STATUS_CODE = 401
FORBIDDEN_ERROR_STATUS_CODE = 403

from __future__ import annotations
from scc_enterprise.core.SCCEnterpriseConsts import INTEGRATION_NAME as SCCE_NAME, SNAKE_INTEGRATION_NAME

INTEGRATION_NAME = "ServiceNow"

SNOW_API_ENDPOINTS = {
    "get_comments": "table/sys_journal_field",
    "get_group_id": "table/sys_user_group",
    "get_incidents": "table/{table}",
    "get_tokens": "oauth_token.do",
    "get_ui_list_elements": "table/sys_ui_list_element?list_id={list_id}",
    "get_user_details": "table/sys_user",
    "tables": "table/{table}",
    "update_incident": "table/{table}/{ticket}",
}
NOT_FOUND_STATUS = 404
CLASS_NOT_FOUND_STATUS = 400

CUSTOM_TICKET_TABLE_NAME = f"u_{SNAKE_INTEGRATION_NAME}_cloud_posture_ticket"
CUSTOM_TICKET_USER = f"{CUSTOM_TICKET_TABLE_NAME}_user"
CUSTOM_TICKET_TABLE_LABEL = f"{SCCE_NAME} Cloud Posture Ticket"
APPLICATION_MODULE_TITLE = f"{SCCE_NAME} Cloud Posture Ticket"
DEFAULT_VIEW = "Default view"

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# A link to the default SNOW timezone documentation:
# https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0594661
DEFAULT_TZ = "US/Pacific"
UTC_TZ = "UTC"

# !IMPORTANT! gs.dateGenerate will generate a DateTime object in local SNow instance tz
INCIDENT_TIME_FILTER = "{column}{operator}javascript:gs.dateGenerate('{date}','{time}')"
ON_OR_AFTER_OPERATOR = ">="
DEFAULT_PAGE_SIZE = 100

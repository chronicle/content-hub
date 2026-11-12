# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module: [constants] defined constants."""
from __future__ import annotations

INTEGRATION_IDENTIFIER = "AtlassianConfluenceServer"
TABLE_NAME = "Available Confluence Pages"

# Action Script Names
PING_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Ping"
LIST_PAGES_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - List Pages"
GET_PAGE_BY_ID_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Page by ID"
GET_CHILD_PAGES_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Child Pages"
GET_PAGE_COMMENTS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Page Comments"
ENDPOINTS = {
    "ping": "/rest/api/content?limit={limit}",
    "list_pages": "/rest/api/content?limit={limit}&expand=space,history",
    "get_page_by_id": "/rest/api/content/{page_id}?expand={expand}",
    "get_child_pages": "/rest/api/content/{page_id}/child/page?limit={limit}",
    "get_page_comments": "/rest/api/content/{page_id}/child/comment?expand={"
    "expand}&limit={limit}",
}

# API Status Codes
API_BAD_REQUEST = 400
API_SERVER_ERROR = 500
API_NOT_FOUND = 404
API_UNAUTHORIZED_ERROR = 401

FILTER_STRATEGY_MAPPING = {
    "Not Specified": "",
    "Equal": lambda item, value: str(item).lower() == str(value).lower(),
    "Contains": lambda item, value: str(value).lower() in str(item).lower(),
}

FILTER_KEY_VALUES = {
    "Select One": "",
    "Title": "title",
    "Space Name": "name",
    "Status": "status",
}

IPV4_REGEXP = r"(\d{1,3})\.\d{1,3}\.\d{1,3}\.\d{1,3}"
IP_MASKING = r"\1.x.x.x"

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

from __future__ import annotations
INTEGRATION_NAME = "EasyVista"
PING_ACTION = f"{INTEGRATION_NAME} - Ping"
GET_EASYVISTA_TICKET_ACTION = f"{INTEGRATION_NAME} - Get EasyVista Ticket"
ADD_COMMENT_TO_TICKET = f"{INTEGRATION_NAME} - Add Comment To Ticket"
WAIT_FOR_TICKET_UPDATE = f"{INTEGRATION_NAME} - Wait For Ticket Update"
CLOSE_EASYVISTA_TICKET = f"{INTEGRATION_NAME} - Close EasyVista Ticket"

DATETIME_FORMAT = "%m/%d/%Y %H:%M:%S"

# Endpoints
PING_QUERY = "{}/requests?max_rows=1"
TICKET_MODIFICATION = "{}/requests/{}"
TICKET_COMMENT = "{}/requests/{}/comment"
TICKET_DESCRIPTION = "{}/requests/{}/description"
TICKET_DOCUMENTS = "{}/requests/{}/documents"
TICKET_ACTIONS = "{}/actions?search=REQUEST.RFC_NUMBER:{}"

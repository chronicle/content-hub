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

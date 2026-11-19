from __future__ import annotations
INTEGRATION_NAME: str = "Zerofox"
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
ADD_NOTE_TO_ALERT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add Note To Alert"
ADD_EVIDENCE_TO_ALERT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add Evidence To Alert"
CLOSE_ALERT_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Close Alert"
REQUEST_TAKEDOWN_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Request Takedown"

ENDPOINTS: dict[str, str] = {
    "get_alert": "/1.0/alerts/?limit=1",
    "add_note": "/1.0/alerts/{alert_id}/append_notes/",
    "close_alert": "/1.0/alerts/{alert_id}/close/",
    "request_takedown": "/1.0/alerts/{alert_id}/request_takedown/",
    "add_evidence_to_alert": "/1.0/alerts/{alert_id}/attachments/"
}
INVALID_TOKEN_ERROR: str = "invalid token."
FAILED_TO_TAKE_REQUEST_DOWN_ERR: str = "failed to take action `request_takedown`"
INVALID_ATTACHMENT_ERR: str = "invalid extension for attachment"

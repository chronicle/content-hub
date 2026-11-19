from __future__ import annotations

import json

from bs4 import BeautifulSoup

from google_cloud_policy_intelligence.core.constants import NOT_FOUND_STATUS, FORBIDDEN_STATUS, RATE_LIMIT_STATUS
from google_cloud_policy_intelligence.core.exceptions import (
    InsufficientResourcePermissionError,
    ProjectNotFoundError,
    GoogleCloudPolicyIntelligenceError,
    MaximumRequestLimitError,
)


def validate_response(status_code: int, content: str | bytes) -> None:
    """Validate response

    Args:
        response_info: The response info from the request API
        content: The response content
    """

    if 200 <= status_code < 400:
        return

    try:
        content = json.loads(content)
    except json.decoder.JSONDecodeError:
        pass

    message = get_error_message_from_response(status_code, content)

    if status_code == FORBIDDEN_STATUS:
        raise InsufficientResourcePermissionError(f"{message}")

    if status_code == NOT_FOUND_STATUS:
        raise ProjectNotFoundError(f"{message}")

    if status_code == RATE_LIMIT_STATUS:
        raise MaximumRequestLimitError(f"{message}")

    raise GoogleCloudPolicyIntelligenceError(f"{message}")


def get_error_message_from_response(
    status_code: int, content: bytes | dict, error_msg: str = "An error occurred"
) -> str:
    """Gets the error message from the response content

    Args:
        status_code: Response status code
        content: Response content
        error_msg: Generic error message to be applied at the beginning of each
            error message
    Returns:
        An error message
    """

    if isinstance(content, dict):
        message = content.get("error", {}).get("message")
        error_text = message
    else:
        error_text = BeautifulSoup(content, "html.parser").p.text
    return f"{error_msg}: {error_text}\nResponse Status Code: {status_code}"

from __future__ import annotations
import json

from web_risk.core.WebRiskExceptions import WebRiskValidationException


def parse_string_to_dict(string):
    """Parse json string to dict.

    Args:
        string (str): string to parse

    Returns:
        dict: parsed dict

    Raises:
        WebRiskValidationException
    """
    try:
        return json.loads(string)
    except Exception as err:
        raise WebRiskValidationException(
            f"Unable to parse provided json. Error is: {err}"
        ) from err

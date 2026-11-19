from __future__ import annotations

import json

from TIPCommon.types import SingleJson

from google_forms.core.exceptions import InvalidJSONFormatException


def parse_string_to_dict(json_string: str) -> SingleJson:
    """Parse json string to dict.

    Args:
        json_string(str): string to parse.

    Returns:
        SingleJson: parsed dict.
    """
    try:
        return json.loads(json_string)

    except json.JSONDecodeError as err:
        raise InvalidJSONFormatException(
            f"Unable to parse provided json. Error is: {err}"
        ) from err

from __future__ import annotations

from typing import Any


def get_filtered_params(params: dict[str, Any]) -> dict[str, Any]:
    """Filter out None values from params.

    Args:
        params (dict): The params dictionary to filter.

    Returns:
        dict: The filtered params dictionary.
    """
    return {k: v for k, v in list(params.items()) if v is not None}

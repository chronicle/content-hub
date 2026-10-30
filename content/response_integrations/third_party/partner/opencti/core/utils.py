from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone

from dateutil import parser as dtparser

SCORE_COLORS = {
    "green": "#99d7ca",
    "yellow": "#fff371",
    "red": "#fa903e",
}

regex_sha512 = r"[0-9a-fA-F]{128}"
regex_sha256 = r"[0-9a-fA-F]{64}"
regex_sha1 = r"[0-9a-fA-F]{40}"
regex_md5 = r"[0-9a-fA-F]{32}"


def convert_date_format(date_str: str) -> str:
    """Convert a date string to ISO 8601 format in UTC.

    Args:
        date_str: A date string in either ISO format or a custom format used by
            Google SOAR.

    Returns:
        A date string in ISO format as UTC.
    """
    if not isinstance(date_str, str):
        raise TypeError(f"Expected a string, got {type(date_str)}")

    try:
        # Preferred path: accept valid ISO datetime strings as-is.
        datetime_obj = datetime.fromisoformat(date_str)
    except ValueError:
        # Fallback path: parse Google SOAR/custom datetime formats and normalize to ISO.
        datetime_obj = dtparser.parse(date_str)

    if datetime_obj.tzinfo:
        datetime_obj = datetime_obj.astimezone(timezone.utc)
    else:
        datetime_obj = datetime_obj.replace(tzinfo=timezone.utc)

    return datetime_obj.isoformat()


def get_hash_type(value: str) -> str | None:
    """Infer hash type from a hexadecimal hash string.

    Args:
        value: Hash string to evaluate.

    Returns:
        The hash algorithm name ("sha512", "sha256", "sha1", or "md5") if the
        input matches a known digest length; otherwise, None.
    """
    if re.fullmatch(regex_sha512, value):
        return "sha512"
    elif re.fullmatch(regex_sha256, value):
        return "sha256"
    elif re.fullmatch(regex_sha1, value):
        return "sha1"
    elif re.fullmatch(regex_md5, value):
        return "md5"
    else:
        return None


def is_ipv4(value: str) -> bool:
    """Determine whether the provided string is an IPv4 address or valid IPv4 CIDR."""
    try:
        ipaddress.IPv4Address(value)  # Check for individual IP
        return True
    except (ipaddress.AddressValueError, TypeError):
        try:
            ipaddress.IPv4Network(value, strict=False)  # Check for CIDR notation
            return True
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, TypeError):
            return False


def parse_csv_list(value: str | None, separator: str = ",") -> list[str]:
    """Parse a comma-separated string into a clean list of non-empty stripped items.

    Used to normalize multi-value action parameters such as Labels.

    Args:
        value: Raw parameter value from the action (may be None or empty).
        separator: Separator character. Defaults to ",".

    Returns:
        List of trimmed, non-empty strings. Empty list if value is falsy.
    """
    if not value:
        return []
    return [item.strip() for item in value.split(separator) if item and item.strip()]


def score_to_color(score: int) -> str:
    """Map a numeric score to an hexadecimal color code."""
    if score >= 50:
        return SCORE_COLORS["red"]
    if score >= 10:
        return SCORE_COLORS["yellow"]
    return SCORE_COLORS["green"]

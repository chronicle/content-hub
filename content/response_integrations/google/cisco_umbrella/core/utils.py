from __future__ import annotations
from urllib.parse import urlparse
from cisco_umbrella.core.exceptions import ValidationError


def get_entity_original_identifier(entity):
    """
    helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def validate_range(value: str | int, v_min: int, v_max: int) -> int:
    """
    Validate that a value is within a given range.
    :param value: The value to validate. Can be a string or an integer.
    :param min: The minimum value of the range.
    :param max: The maximum value of the range.
    :return: The value as an integer.
    :raises ValidationError: If the value is not within the range.
    """
    if isinstance(value, str):
        value = int(value)

    if not v_min <= value <= v_max:
        raise ValidationError(f"Value must be between {v_min} and {v_max}")

    return value


def get_hostname(url: str) -> str:
    """
    Extracts the full hostname (including subdomains like 'www') from a URL.
    """
    # Ensure the URL has a scheme for correct parsing if missing
    if "://" not in url:
        url = "https://" + url
    parsed_uri = urlparse(url)
    return parsed_uri.hostname

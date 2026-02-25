from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from .constants import INTEGRATION_NAME
from .cyware_exceptions import InvalidFormatException, InvalidIntegerException


def get_integration_params(siemplify: Any) -> Tuple[str, str, str, bool]:
    """
    Retrieve the integration parameters from Siemplify configuration.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        tuple: A tuple containing (base_url, access_id, secret_key, verify_ssl).
    """
    base_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Base URL", input_type=str, is_mandatory=True
    )
    access_id = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Access ID",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )
    secret_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Secret Key",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Verify SSL", input_type=bool, is_mandatory=False, default_value=False
    )

    return base_url, access_id, secret_key, verify_ssl


def validate_integer_param(
    value: Any,
    param_name: str,
    zero_allowed: bool = False,
    allow_negative: bool = False,
    max_value: Optional[int] = None,
) -> int:
    """
    Validates if the given value is an integer and meets the specified requirements.

    Args:
        value (int|str): The value to be validated.
        param_name (str): The name of the parameter for error messages.
        zero_allowed (bool, optional): If True, zero is a valid integer. Defaults to False.
        allow_negative (bool, optional): If True, negative integers are allowed. Defaults to False.
        max_value (int, optional): If set, value must be less than or equal to max value.

    Raises:
        InvalidIntegerException: If the value is not a valid integer or does not meet the rules.

    Returns:
        int: The validated integer value.
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise InvalidIntegerException(f"{param_name} must be an integer.")
    if not allow_negative and int_value < 0:
        raise InvalidIntegerException(f"{param_name} must be a non-negative integer.")
    if not zero_allowed and int_value == 0:
        raise InvalidIntegerException(f"{param_name} must be greater than zero.")
    if max_value and int_value > max_value:
        raise InvalidIntegerException(
            f"{param_name} value must be less than or equal to {max_value}."
        )
    return int_value


def string_to_list(
    items_str: Optional[str], strip_quotes: bool = False, param_name: str = "Items"
) -> List[str]:
    """
    Convert comma-separated string to list.

    Args:
        items_str (str): Comma-separated string
        strip_quotes (bool): If True, use CSV parsing to handle quoted values properly.
        param_name (str): Parameter name for error messaging.

    Returns:
        list: List of strings

    Raises:
        InvalidFormatException: If CSV parsing fails when strip_quotes is True
    """
    if not items_str:
        return []
    
    if strip_quotes:
        import csv
        import io
        
        try:
            # Use csv.reader to properly parse comma-separated values with quotes
            reader = csv.reader(io.StringIO(items_str.strip()), skipinitialspace=True)
            items = next(reader, [])
            # Strip whitespace from each item
            return [item.strip() for item in items if item.strip()]
        except csv.Error as e:
            raise InvalidFormatException(
                f"{param_name} format is invalid. CSV parsing error: {str(e)}"
            )
        except Exception as e:
            raise InvalidFormatException(
                f"{param_name} format is invalid. Error: {str(e)}"
            )

    return [item.strip() for item in items_str.split(",") if item.strip()]


def validate_json_string(json_str: Optional[str], param_name: str) -> Dict[str, Any]:
    """
    Validate and parse JSON string.

    Args:
        json_str (str): JSON string to validate
        param_name (str): Parameter name for error messages

    Returns:
        dict: Parsed JSON object

    Raises:
        ValueError: If JSON is invalid
    """
    if not json_str or not json_str.strip():
        raise ValueError(f"{param_name} must be a non-empty JSON string.")

    try:
        json_obj = json.loads(json_str)
        if not isinstance(json_obj, dict):
            raise ValueError(f"{param_name} must be a JSON object.")
        return json_obj
    except json.JSONDecodeError as e:
        raise ValueError(f"{param_name} must be valid JSON. Error: {str(e)}")


def clean_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None values from a dictionary."""
    return {k: v for k, v in params.items() if v is not None}


def get_entities(siemplify: Any) -> List[str]:
    """Return the identifier of every target entity attached to the case."""
    entities = getattr(siemplify, "target_entities", []) or []
    return [
        str(entity.identifier).strip() for entity in entities if getattr(entity, "identifier", None)
    ]


def get_entities_object(siemplify: Any) -> List[str]:
    """Return the list of every target entity attached to the case."""
    return [entity for entity in siemplify.target_entities]


def sanitize_url(url: str) -> str:
    """
    Sanitize URL by removing sensitive query parameters like AccessID, Signature, and Expires.

    Args:
        url (str): The URL to sanitize

    Returns:
        str: Sanitized URL with sensitive parameters masked
    """
    try:
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # List of sensitive parameters to mask
        sensitive_params = ["AccessID", "Signature", "Expires", "access_id", "signature", "expires"]

        # Remove sensitive parameters
        sanitized_params = {k: v for k, v in query_params.items() if k not in sensitive_params}

        # Add masked indicators for removed params
        if any(param in query_params for param in sensitive_params):
            sanitized_params["[REDACTED]"] = ["Sensitive authentication parameters hidden"]

        # Reconstruct URL
        new_query = urlencode(sanitized_params, doseq=True)
        sanitized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))

        return sanitized
    except Exception:
        # If sanitization fails, return a generic message
        return url.split("?")[0] + "?[REDACTED]"

"""Common helper methods used across the entire integration."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from dateutil import parser
from soar_sdk.SiemplifyUtils import unix_now

from .constants import (
    DATE_PARAMETERS,
    DEFAULT_EXPIRY_SECONDS,
    ERRORS,
    EXPIRES_IN_KEY,
    INTEGRATION_NAME,
    POSSIBLE_LIST_PARAM_VALUES,
    POSSIBLE_OPERATORS,
    POSSIBLE_PARAMETERS,
    STRINGIFIED_LIST_PARAMETERS,
)


def make_aware(dt):
    """Ensure datetime is timezone-aware (UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)  # Convert naive to UTC-aware
    return dt.astimezone(UTC)  # Convert any timezone to UTC


def normalize_js_date(date_str):
    """Convert a JS-style (Sat Mar 15 2025 14:55:48 GMT+0000 (Coordinated Universal Time))
    date to a datetime object."""
    pattern = r"(\w{3}) (\w{3}) (\d{1,2}) (\d{4}) (\d{2}:\d{2}:\d{2}) (?:GMT|UTC)?([+-]\d{4})?"
    match = re.search(pattern, date_str)

    if match:
        _day_of_week, month, day, year, time, offset = match.groups()
        offset = offset or "+0000"  # Default to UTC if no offset is found
        date_str = f"{day} {month} {year} {time} {offset}"
        return datetime.strptime(date_str, "%d %b %Y %H:%M:%S %z")

    raise ValueError(ERRORS["VALIDATIONS"]["INVALID_DATE_FORMAT"].format(date_str))


def parse_the_date(date_string):
    """Parse a date string according to the following rules.

    1. If the string contains a JavaScript-style date with an explicit GMT offset
       (e.g. "Sat Aug 12 2017 12:00:00 GMT-0700"),
       use regex-based parsing to extract the date components and create a datetime object.
    2. Otherwise, use `dateutil.parser.parse()` to parse the date string.

    Raise ValueError if the date string cannot be parsed.
    Returns a datetime object representing the parsed date.
    """
    # Category 1: Use regex-based parsing for JavaScript-style date with explicit GMT offset
    if re.search(r"GMT[+-]\d{4}", date_string):
        parsed_date = normalize_js_date(date_string)
    else:
        # Category 2: Use `dateutil.parser.parse()` for all other cases
        parsed_date = parser.parse(date_string)
    timezone_aware_date = make_aware(parsed_date)
    return timezone_aware_date


def get_integration_params(siemplify):
    """Retrieve the integration parameters from Siemplify configuration.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        tuple: A tuple containing the integration parameters.

    """
    authentication_type = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Access Token Based Authentication",
        input_type=bool,
    )
    base_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Base URL",
        input_type=str,
    ).strip()
    api_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "API Key",
        input_type=str,
    ).strip()

    return authentication_type, base_url, api_key


def convert_string(string):
    """Convert the input string to the appropriate type and return its value.

    Args:
        string (str): Input string to be converted.

    Returns:
        bool|int|str|float: Return converted value.

    """
    stripped_string = string.strip()
    lower_string = stripped_string.lower()
    if lower_string == "true":
        return True

    if lower_string == "false":
        return False

    try:
        return int(lower_string)
    except ValueError:
        try:
            return float(lower_string)
        except ValueError:
            return stripped_string


def validate_push_breach_point_inputs(
    parameter: str,
    operator: str,
    value: str,
) -> tuple[bool, (str | int | float | datetime)]:
    """Validate the inputs for Push Breach Point Data action.

    Args:
        parameter (str): Parameter name.
        operator (str): Operator name.
        value (bool|int|str|float): Value.

    Returns:
        str: tuple: Boolean indicating validity, and error message, if invalid, or,
            converted value, if valid.

    """
    if not value:
        return (False, ERRORS["VALIDATIONS"]["EMPTY_VALUE"])

    if parameter not in POSSIBLE_PARAMETERS:
        return (False, ERRORS["VALIDATIONS"]["INCORRECT_PARAMETER"].format(parameter))

    if operator not in POSSIBLE_OPERATORS:
        return False, ERRORS["VALIDATIONS"]["INCORRECT_OPERATOR"].format(operator)

    if parameter == "entityID" and operator not in {"Equals", "Not equal to"}:
        return False, ERRORS["VALIDATIONS"]["ENTITY_ID_INCORRECT_OPERATOR"]

    if parameter in STRINGIFIED_LIST_PARAMETERS and operator not in {
        "Contains",
        "Not Contains",
    }:
        return False, ERRORS["VALIDATIONS"]["CONTAINS_INCORRECT_PARAMETER"].format(
            parameter,
        )

    if operator in {"Contains", "Not Contains"} and parameter not in STRINGIFIED_LIST_PARAMETERS:
        return False, ERRORS["VALIDATIONS"]["CONTAINS_INCORRECT_OPERATOR"].format(
            parameter,
        )

    if parameter in POSSIBLE_LIST_PARAM_VALUES:
        upper_value = value.upper()
        if upper_value not in POSSIBLE_LIST_PARAM_VALUES[parameter]:
            return False, ERRORS["VALIDATIONS"]["INCORRECT_VALUE_FOR_LIST"].format(
                parameter,
                POSSIBLE_LIST_PARAM_VALUES[parameter],
            )

    if parameter in DATE_PARAMETERS:
        try:
            parsed_date = parse_the_date(value)
            return True, parsed_date
        except ValueError:
            return False, ERRORS["VALIDATIONS"]["INVALID_DATE_FORMAT"].format(value)

    value_input = convert_string(value)

    if parameter not in STRINGIFIED_LIST_PARAMETERS and (
        isinstance(value_input, (str, bool)) and operator not in {"Equals", "Not equal to"}
    ):
        return False, ERRORS["VALIDATIONS"]["INCORRECT_VALUE_TYPE"]

    return True, value_input


def string_to_list(labels_string):
    """Convert a comma-separated string of labels into a list of strings.

    Args:
        labels_string (str): A comma-separated string of labels.

    Returns:
        list[str]: A list of strings, with each string being a label.

    """
    labels_list = labels_string.strip().split(",")
    return [convert_string(label) for label in labels_list]


def convert_to_numeric(value):
    """Convert the input value to an number.

    Args:
        value (str): Input value to be converted.

    Returns:
        float|int: Converted numeric value.

    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0


def generate_encryption_key(api_key: str, base_url: str) -> str:
    """Generate a deterministic encryption key from existing settings.

    Uses PBKDF2-HMAC with SHA-256, a deterministic salt, and a high iteration
    count to derive a fixed-length key suitable for symmetric operations.
    """
    salt = base_url.encode()
    key_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        api_key.encode(),
        salt,
        200_000,
        dklen=32,
    )
    return key_bytes.hex()


def compute_expiry(response):
    now_ms = unix_now()
    expires_in = response.get(EXPIRES_IN_KEY)
    if expires_in is not None:
        try:
            # Most OAuth providers send expires_in as seconds
            expires_in_sec = int(expires_in)
            # Convert seconds → milliseconds
            return now_ms + (expires_in_sec * 1000)

        except (TypeError, ValueError):
            pass
    return now_ms + (DEFAULT_EXPIRY_SECONDS * 1000)

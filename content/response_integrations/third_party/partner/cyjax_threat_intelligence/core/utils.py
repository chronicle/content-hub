from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from .constants import INTEGRATION_NAME
from .cyjax_exceptions import InvalidIntegerException


def get_integration_params(siemplify: Any) -> tuple[str, bool]:
    """
    Retrieve the integration parameters from Siemplify configuration.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        tuple: A tuple containing (api_token, verify_ssl).
    """
    api_token = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=False,
    )

    return api_token, verify_ssl


def parse_date(date_str: str):
    """
    Validate if date_str matches YYYY-MM-DDTHH:MM:SSZ.
    """
    if date_str and date_str.strip():
        date_str = date_str.strip()
    else:
        return None
    date_format = "%Y-%m-%dT%H:%M:%SZ"  # e.g. 2011-11-11T23:59:59Z

    try:
        datetime.strptime(date_str, date_format)
    except ValueError:
        raise ValueError("The Date needs to be in YYYY-MM-DDTHH:MM:SSZ format.")


def validate_integer(
    value: Any,
    param_name: str,
    default_value: int = None,
    zero_allowed: bool = False,
    allow_negative: bool = False,
    max_value: Optional[int] = None,
) -> int | None:
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
        int | None: The validated integer value or None if not provided and no default.
    """
    if value and value.strip():
        value = value.strip()
    else:
        if default_value is not None:
            return default_value
        else:
            return None
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


def get_entity_objects(siemplify: Any) -> List[Any]:
    """Return the list of every target entity attached to the case."""
    return [entity for entity in siemplify.target_entities]


def remove_ioc_enrichment(entity) -> None:
    """
    Clear old Cyjax IOC enrichment data from entity by setting values to "-".

    Args:
        entity: Entity object to clean
    """
    if not hasattr(entity, "additional_properties"):
        return

    # Clear IOC enrichment keys
    for key in entity.additional_properties.keys():
        if key.startswith("Cyjax_"):
            entity.additional_properties[key] = "-"

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_configuration_param
from akamai_integration.core import constants
from akamai_integration.core import exceptions
from akamai_integration.core.datamodels import IntegrationParameters

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


def get_integration_parameters(soar_action: ChronicleSOAR) -> IntegrationParameters:
    """Get the parameters object for Akamai's auth and api manager

    Args:
        soar_action (ChronicleSOAR): SiemplifyAction object.

    Returns:
        IntegrationParameters: IntegrationParameters object.

    """
    api_root: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Host",
        is_mandatory=True,
    )
    client_token: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Client Token",
        is_mandatory=True,
        remove_whitespaces=True,
    )
    client_secret: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        remove_whitespaces=True,
    )
    access_token: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Access Token",
        is_mandatory=True,
        remove_whitespaces=True,
    )
    verify_ssl: bool = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
    )
    integration_params: IntegrationParameters = IntegrationParameters(
        api_root=api_root,
        client_token=client_token,
        client_secret=client_secret,
        access_token=access_token,
        verify_ssl=verify_ssl,
        siemplify_logger=soar_action.LOGGER,
    )

    return integration_params


def validate_iso8601_date_format(date_str: str) -> None:
    """Validate if the given date string is a valid ISO 8601 date format.

    Args:
        date_str (str): The date string to validate.

    Raises:
        exceptions.AkamaiManagerError: If the date string is not a valid
            ISO 8601 date format.

    """
    try:
        datetime.fromisoformat(date_str)

    except ValueError as e:
        raise exceptions.AkamaiManagerError(
            'Provide a value for the "Item Expiration Date" in ISO 8601 format.',
        ) from e

def is_reason_indicating_not_found(reason_text: str) -> bool:
    """
    Checks if the given error reason text indicates a "not found" type of error
    based on predefined patterns in constants.COULD_NOT_BE_FOUND_ERR_LIST.

    Args:
        reason_text (str): The error message or reason string.

    Returns:
        bool: True if the reason indicates a "not found" error, False otherwise.
    """
    if not isinstance(reason_text, str):
        return False
    return any(
        err_pattern in reason_text.lower()
        for err_pattern in constants.COULD_NOT_BE_FOUND_ERR_LIST
    )

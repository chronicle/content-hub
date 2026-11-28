from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_script_param

from .constants import (
    BREACH_HOUSE_KEY_PARAM,
    DEFAULT_VERIFY_SSL,
    HAVEIBEENRANSOM_KEY_PARAM,
    INTEGRATION_IDENTIFIER,
    USER_AGENT,
    VERIFY_SSL_PARAM,
)
from .exceptions import DarkEyeConfigurationError

if TYPE_CHECKING:
    from requests import Session
    from TIPCommon.types import ChronicleSOAR


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationParameters:
    haveibeenransom_api_key: str
    breach_house_api_key: str
    verify_ssl: bool


def build_integration_params(soar_action: ChronicleSOAR) -> IntegrationParameters:
    """Extract the integration configuration.

    Args:
        soar_action: ChronicleSOAR SDK object.

    Returns:
        IntegrationParameters: The configuration.

    Raises:
        DarkEyeConfigurationError: If neither API key is configured.
    """
    input_dictionary = soar_action.get_configuration(INTEGRATION_IDENTIFIER)
    haveibeenransom_api_key: str = extract_script_param(
        soar_action,
        input_dictionary=input_dictionary,
        param_name=HAVEIBEENRANSOM_KEY_PARAM,
        default_value="",
    )
    breach_house_api_key: str = extract_script_param(
        soar_action,
        input_dictionary=input_dictionary,
        param_name=BREACH_HOUSE_KEY_PARAM,
        default_value="",
    )
    verify_ssl: bool = extract_script_param(
        soar_action,
        input_dictionary=input_dictionary,
        param_name=VERIFY_SSL_PARAM,
        default_value=DEFAULT_VERIFY_SSL,
        input_type=bool,
        print_value=True,
    )
    params = IntegrationParameters(
        haveibeenransom_api_key=(haveibeenransom_api_key or "").strip(),
        breach_house_api_key=(breach_house_api_key or "").strip(),
        verify_ssl=verify_ssl,
    )
    if not params.haveibeenransom_api_key and not params.breach_house_api_key:
        msg: str = f"Configure the {HAVEIBEENRANSOM_KEY_PARAM}, the {BREACH_HOUSE_KEY_PARAM} or both."
        raise DarkEyeConfigurationError(msg)
    return params


def create_session(verify_ssl: bool) -> Session:
    """Create the HTTP session shared by both products.

    The API keys are not stored on the session: each request carries the key of its own
    product, so a key is never sent to the other product.

    Args:
        verify_ssl: Whether to validate SSL certificates.

    Returns:
        Session: The session.
    """
    session: Session = CreateSession.create_session()
    session.verify = verify_ssl
    session.headers.update({"Accept": "application/json", "User-Agent": USER_AGENT})
    return session

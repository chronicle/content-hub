"""Authentication module for Silverfort integration."""

from __future__ import annotations

import dataclasses
import time
from typing import TYPE_CHECKING

import jwt  # type: ignore[import-not-found]
from requests import Session
from soar_sdk.SiemplifyAction import SiemplifyAction  # type: ignore[import-not-found]
from soar_sdk.SiemplifyConnectors import (  # type: ignore[import-not-found]
    SiemplifyConnectorExecution,
)
from soar_sdk.SiemplifyJob import SiemplifyJob  # type: ignore[import-not-found]
from TIPCommon.base.interfaces import Authable  # type: ignore[import-not-found]
from TIPCommon.base.utils import CreateSession  # type: ignore[import-not-found]
from TIPCommon.extraction import extract_script_param  # type: ignore[import-not-found]

from .constants import (
    API_KEY_HEADER,
    AUTHORIZATION_HEADER,
    DEFAULT_VERIFY_SSL,
    INTEGRATION_IDENTIFIER,
    JWT_ALGORITHM,
    JWT_EXPIRATION_SECONDS,
    ApiType,
)
from .data_models import AppCredentials, IntegrationParameters
from .exceptions import SilverfortConfigurationError, SilverfortCredentialsNotConfiguredError

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR  # type: ignore[import-not-found]


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    """Parameters for session authentication."""

    api_root: str
    external_api_key: str
    verify_ssl: bool
    app_credentials: AppCredentials | None = None
    api_type: ApiType | None = None


class JWTAuthenticator:
    """JWT token generator for Silverfort API authentication."""

    def __init__(self, app_user_id: str, app_user_secret: str) -> None:
        """Initialize the JWT authenticator.

        Args:
            app_user_id: The App User ID (used as issuer claim).
            app_user_secret: The App User Secret (used as signing key).
        """
        self.app_user_id = app_user_id
        self.app_user_secret = app_user_secret

    def generate_token(self) -> str:
        """Generate a JWT token for API authentication.

        Returns:
            JWT token string.
        """
        current_time = int(time.time())
        payload = {
            "issuer": self.app_user_id,
            "iat": current_time,
            "exp": current_time + JWT_EXPIRATION_SECONDS,
        }
        return jwt.encode(payload, self.app_user_secret, algorithm=JWT_ALGORITHM)


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Extract authentication parameters from SOAR SDK object.

    Args:
        soar_sdk_object: ChronicleSOAR SDK object (Action, Connector, or Job).

    Returns:
        IntegrationParameters object with extracted credentials.

    Raises:
        SilverfortConfigurationError: If SDK object type is not supported.
    """
    sdk_class = type(soar_sdk_object).__name__

    if sdk_class == SiemplifyAction.__name__:
        input_dictionary = soar_sdk_object.get_configuration(INTEGRATION_IDENTIFIER)
    elif sdk_class in (SiemplifyConnectorExecution.__name__, SiemplifyJob.__name__):
        input_dictionary = soar_sdk_object.parameters
    else:
        raise SilverfortConfigurationError(
            f"Provided SOAR instance is not supported! type: {sdk_class}."
        )

    api_root = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    external_api_key = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="External API Key",
        is_mandatory=True,
    )

    verify_ssl = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        default_value=DEFAULT_VERIFY_SSL,
        input_type=bool,
        is_mandatory=False,
        print_value=True,
    )

    # Risk API credentials (optional)
    risk_app_user_id = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Risk App User ID",
        is_mandatory=False,
    )
    risk_app_user_secret = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Risk App User Secret",
        is_mandatory=False,
    )

    # Service Accounts API credentials (optional)
    service_accounts_app_user_id = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Service Accounts App User ID",
        is_mandatory=False,
    )
    service_accounts_app_user_secret = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Service Accounts App User Secret",
        is_mandatory=False,
    )

    # Policies API credentials (optional)
    policies_app_user_id = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Policies App User ID",
        is_mandatory=False,
    )
    policies_app_user_secret = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Policies App User Secret",
        is_mandatory=False,
    )

    return IntegrationParameters(
        api_root=api_root.rstrip("/"),
        external_api_key=external_api_key,
        verify_ssl=verify_ssl,
        risk_app_user_id=risk_app_user_id,
        risk_app_user_secret=risk_app_user_secret,
        service_accounts_app_user_id=service_accounts_app_user_id,
        service_accounts_app_user_secret=service_accounts_app_user_secret,
        policies_app_user_id=policies_app_user_id,
        policies_app_user_secret=policies_app_user_secret,
    )


def get_app_credentials(
    params: IntegrationParameters,
    api_type: ApiType,
) -> AppCredentials:
    """Get app credentials for a specific API type.

    Args:
        params: Integration parameters containing all credentials.
        api_type: Type of API to get credentials for.

    Returns:
        AppCredentials for the specified API type.

    Raises:
        SilverfortCredentialsNotConfiguredError: If credentials are not configured.
    """
    credential_map = {
        ApiType.RISK: (params.risk_app_user_id, params.risk_app_user_secret),
        ApiType.SERVICE_ACCOUNTS: (
            params.service_accounts_app_user_id,
            params.service_accounts_app_user_secret,
        ),
        ApiType.POLICIES: (params.policies_app_user_id, params.policies_app_user_secret),
    }

    user_id, user_secret = credential_map.get(api_type, (None, None))

    if not user_id or not user_secret:
        raise SilverfortCredentialsNotConfiguredError(api_type.value.replace("_", " ").title())

    return AppCredentials(app_user_id=user_id, app_user_secret=user_secret)


def get_configured_api_types(params: IntegrationParameters) -> list[ApiType]:
    """Get list of API types that have credentials configured.

    Args:
        params: Integration parameters containing all credentials.

    Returns:
        List of ApiType enums for which credentials are configured.
    """
    configured = []

    if params.risk_app_user_id and params.risk_app_user_secret:
        configured.append(ApiType.RISK)
    if params.service_accounts_app_user_id and params.service_accounts_app_user_secret:
        configured.append(ApiType.SERVICE_ACCOUNTS)
    if params.policies_app_user_id and params.policies_app_user_secret:
        configured.append(ApiType.POLICIES)

    return configured


class AuthenticatedSession(Authable):
    """Authenticated session for Silverfort API requests."""

    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        """Authenticate the session with Silverfort credentials.

        Args:
            params: Session authentication parameters.
        """
        self.session = get_authenticated_session(session_parameters=params)


def get_authenticated_session(session_parameters: SessionAuthenticationParameters) -> Session:
    """Get an authenticated session for API requests.

    Args:
        session_parameters: Authentication parameters.

    Returns:
        Authenticated requests Session object.
    """
    session: Session = CreateSession.create_session()
    _authenticate_session(session, session_parameters=session_parameters)
    return session


def _authenticate_session(
    session: Session,
    session_parameters: SessionAuthenticationParameters,
) -> None:
    """Configure session with authentication headers.

    Args:
        session: Requests session to configure.
        session_parameters: Authentication parameters.
    """
    session.verify = session_parameters.verify_ssl

    # Add External API Key header (always required)
    session.headers.update({
        API_KEY_HEADER: session_parameters.external_api_key,
    })

    # Add JWT Bearer token if app credentials are provided
    if session_parameters.app_credentials:
        jwt_authenticator = JWTAuthenticator(
            app_user_id=session_parameters.app_credentials.app_user_id,
            app_user_secret=session_parameters.app_credentials.app_user_secret,
        )
        jwt_token = jwt_authenticator.generate_token()
        session.headers.update({
            AUTHORIZATION_HEADER: f"Bearer {jwt_token}",
        })

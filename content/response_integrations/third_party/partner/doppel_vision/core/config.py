from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import TYPE_CHECKING

import requests

from .auth_provider_v1 import AuthProviderV1
from .auth_provider_v2 import AuthProviderV2
from .constants import (
    API_VERSION_V1,
    API_VERSION_V2,
    INTEGRATION_NAME,
    PARAM_API_KEY,
    PARAM_API_VERSION,
    PARAM_CLIENT_ID,
    PARAM_CLIENT_SECRET,
    PARAM_ORG_CODE,
    PARAM_USER_API_KEY,
    SUPPORTED_API_VERSIONS,
)
from .exceptions import DoppelConfigError
from .token_cache import TokenCache

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR, SingleJson

    from .DoppelManager import DoppelManager


@dataclass(frozen=True, slots=True)
class IntegrationConfig:
    """Validated Doppel Vision instance configuration.

    Attributes:
        api_version: Resolved API version (`v1` or `v2`).
        api_key: Organization API key used by v1.
        user_api_key: Optional user API key used by v1.
        org_code: Optional organization code used by v1.
        client_id: OAuth client ID used by v2.
        client_secret: OAuth client secret used by v2.
    """

    api_version: str
    api_key: str | None = None
    user_api_key: str | None = None
    org_code: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_api_version(raw_value: object) -> str:
    """Resolve a user-entered API version to v1 or v2.

    Missing/blank values default to v1 so existing installs keep working.

    Args:
        raw_value: Raw API version value from configuration.

    Returns:
        Canonical API version (`v1` or `v2`).

    Raises:
        DoppelConfigError: If the value is present but not a supported version.
    """
    cleaned = _clean(raw_value)
    if not cleaned:
        return API_VERSION_V1

    normalized = cleaned.lower()
    if normalized in {API_VERSION_V1, "1"} or normalized.startswith("v1"):
        return API_VERSION_V1
    if normalized in {API_VERSION_V2, "2"} or normalized.startswith("v2"):
        return API_VERSION_V2
    raise DoppelConfigError(
        f"API Version must be {' or '.join(SUPPORTED_API_VERSIONS)}. Received an unsupported value.",
    )


_PARAM_NAMES: tuple[str, ...] = (
    PARAM_API_VERSION,
    PARAM_API_KEY,
    PARAM_USER_API_KEY,
    PARAM_ORG_CODE,
    PARAM_CLIENT_ID,
    PARAM_CLIENT_SECRET,
)


def validate_config(config: IntegrationConfig) -> IntegrationConfig:
    """Validate that the selected API version has the required credentials.

    Args:
        config: Integration configuration to validate.

    Returns:
        The same configuration when it is valid.

    Raises:
        DoppelConfigError: If required credentials for the selected version are missing.
    """
    if config.api_version == API_VERSION_V2:
        if not config.client_id or not config.client_secret:
            raise DoppelConfigError("Client ID and Client Secret are required for API v2")
        return config
    if not config.api_key:
        raise DoppelConfigError("API Key is required for API v1")
    return config


def _configuration_mapping(siemplify: ChronicleSOAR) -> SingleJson | None:
    """Return the raw configuration dictionary from a Siemplify/SOAR SDK object.

    Action and connector objects expose ``siemplify.configuration`` directly.
    Job objects (``SiemplifyJob``) only expose it via ``get_configuration()``.
    """
    getter = getattr(siemplify, "get_configuration", None)
    if not callable(getter):
        return None
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            configuration = getter(INTEGRATION_NAME)
    except Exception:
        return None
    if isinstance(configuration, dict):
        return configuration
    return None


def _extract_param(siemplify: ChronicleSOAR, param_name: str) -> str | None:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            val: object = siemplify.extract_configuration_param(
                provider_name=INTEGRATION_NAME,
                param_name=param_name,
                default_value="",
                is_mandatory=False,
                print_value=False,
            )
    except Exception:
        val = ""
    return _clean(val)


def _read_params(siemplify: ChronicleSOAR) -> dict[str, str | None]:
    mapping = _configuration_mapping(siemplify)
    if mapping is not None:
        return {name: _clean(mapping.get(name)) for name in _PARAM_NAMES}
    return {name: _extract_param(siemplify, name) for name in _PARAM_NAMES}


def load_integration_config(siemplify: ChronicleSOAR) -> IntegrationConfig:
    """Load and validate Doppel Vision configuration from a SOAR SDK object.

    Args:
        siemplify: SOAR SDK object exposing instance configuration.

    Returns:
        Validated integration configuration.
    """
    params = _read_params(siemplify)
    config = IntegrationConfig(
        api_version=resolve_api_version(params[PARAM_API_VERSION]),
        api_key=params[PARAM_API_KEY],
        user_api_key=params[PARAM_USER_API_KEY],
        org_code=params[PARAM_ORG_CODE],
        client_id=params[PARAM_CLIENT_ID],
        client_secret=params[PARAM_CLIENT_SECRET],
    )
    return validate_config(config)


def create_auth_provider(
    config: IntegrationConfig,
    siemplify: ChronicleSOAR | None = None,
    session: requests.Session | None = None,
    *,
    persist_token: bool = True,
) -> AuthProviderV1 | AuthProviderV2:
    """Create the auth provider that matches the selected API version.

    Args:
        config: Validated integration configuration.
        siemplify: Optional SOAR SDK object used to persist v2 tokens.
        session: Optional shared requests session.
        persist_token: Whether v2 tokens should be stored in SOAR context.

    Returns:
        Configured v1 or v2 authentication provider.
    """
    if config.api_version == API_VERSION_V2:
        return AuthProviderV2(
            client_id=config.client_id or "",
            client_secret=config.client_secret or "",
            token_cache=TokenCache(siemplify=siemplify, use_context=persist_token),
            session=session,
        )
    return AuthProviderV1(api_key=config.api_key or "", user_api_key=config.user_api_key, org_code=config.org_code)


def create_manager_from_siemplify(
    siemplify: ChronicleSOAR,
    *,
    persist_token: bool = True,
) -> DoppelManager:
    """Create a configured DoppelManager instance from a SOAR SDK object."""
    from .DoppelManager import DoppelManager

    config = load_integration_config(siemplify)
    return DoppelManager.from_config(config, siemplify=siemplify, persist_token=persist_token)

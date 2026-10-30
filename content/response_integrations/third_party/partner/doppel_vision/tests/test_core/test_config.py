from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from core.config import (
    IntegrationConfig,
    create_auth_provider,
    load_integration_config,
    resolve_api_version,
    validate_config,
)
from core.constants import API_VERSION_V1, API_VERSION_V2
from core.exceptions import DoppelConfigError


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, API_VERSION_V1),
        ("", API_VERSION_V1),
        ("v1", API_VERSION_V1),
        ("V1", API_VERSION_V1),
        ("1", API_VERSION_V1),
        ("V1 (API Key)", API_VERSION_V1),
        ("v2", API_VERSION_V2),
        ("V2", API_VERSION_V2),
        ("2", API_VERSION_V2),
        ("V2 (OAuth 2.0 Client Credentials)", API_VERSION_V2),
    ],
)
def test_resolve_api_version(raw: str | None, expected: str) -> None:
    assert resolve_api_version(raw) == expected


def test_resolve_api_version_rejects_unknown() -> None:
    with pytest.raises(DoppelConfigError):
        resolve_api_version("v3")


def test_validate_v1_requires_api_key() -> None:
    with pytest.raises(DoppelConfigError, match="API Key is required"):
        validate_config(IntegrationConfig(api_version=API_VERSION_V1, api_key=None))


def test_validate_v2_requires_client_credentials() -> None:
    with pytest.raises(DoppelConfigError, match="Client ID and Client Secret"):
        validate_config(IntegrationConfig(api_version=API_VERSION_V2, client_id="id"))


def test_existing_v1_config_without_new_fields_still_loads() -> None:
    siemplify = MagicMock()

    def extract(provider_name: str, param_name: str, **_kwargs):
        del provider_name
        return {
            "API Version": None,
            "API Key": "existing-key",
            "User API Key": "user-key",
            "Organization Code": "ACM",
            "Client ID": None,
            "Client Secret": None,
        }.get(param_name)

    siemplify.extract_configuration_param.side_effect = extract
    config = load_integration_config(siemplify)
    assert config.api_version == API_VERSION_V1
    assert config.api_key == "existing-key"
    assert config.user_api_key == "user-key"
    assert config.org_code == "ACM"
    assert config.client_id is None
    assert config.client_secret is None


def test_v2_config_loads_client_credentials() -> None:
    siemplify = MagicMock()

    def extract(provider_name: str, param_name: str, **_kwargs):
        del provider_name
        return {
            "API Version": "v2",
            "API Key": None,
            "User API Key": None,
            "Organization Code": None,
            "Client ID": "client-id",
            "Client Secret": "client-secret",
        }.get(param_name)

    siemplify.extract_configuration_param.side_effect = extract
    config = load_integration_config(siemplify)
    assert config.api_version == API_VERSION_V2
    assert config.client_id == "client-id"
    assert config.client_secret == "client-secret"


def test_reads_config_mapping_without_extracting_empty_params() -> None:
    siemplify = MagicMock()
    siemplify.get_configuration.return_value = {
        "API Version": "v2",
        "API Key": "",
        "User API Key": "",
        "Organization Code": "",
        "Client ID": "client-id",
        "Client Secret": "client-secret",
    }
    config = load_integration_config(siemplify)
    assert config.api_version == API_VERSION_V2
    assert config.api_key is None
    siemplify.extract_configuration_param.assert_not_called()


def test_v1_missing_api_key_raises_clear_error_from_mapping() -> None:
    siemplify = MagicMock()
    siemplify.get_configuration.return_value = {
        "API Version": "v1",
        "API Key": "",
        "Client ID": "client-id",
        "Client Secret": "client-secret",
    }
    with pytest.raises(DoppelConfigError, match="API Key is required for API v1"):
        load_integration_config(siemplify)


def test_v2_auth_provider_persists_token_by_default() -> None:
    siemplify = MagicMock()
    siemplify.integration_instance = "instance-1"
    provider = create_auth_provider(
        IntegrationConfig(api_version=API_VERSION_V2, client_id="id", client_secret="secret"),
        siemplify=siemplify,
    )
    assert provider.token_cache.siemplify is siemplify


def test_v2_auth_provider_can_disable_token_persist() -> None:
    siemplify = MagicMock()
    provider = create_auth_provider(
        IntegrationConfig(api_version=API_VERSION_V2, client_id="id", client_secret="secret"),
        siemplify=siemplify,
        persist_token=False,
    )
    assert provider.token_cache.siemplify is None

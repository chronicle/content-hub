from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def spycloud_sdk() -> MagicMock:
    """Mock SpyCloud SDK with a successful breach catalog ping by default."""
    sdk = MagicMock()
    sdk.breach_catalog.ping.return_value = True
    return sdk


@pytest.fixture(autouse=True)
def patch_spycloud_sdk(spycloud_sdk: MagicMock):
    """Patch the SpyCloudSDK used by actions so no real HTTP calls are made."""
    with patch(
        "spy_cloud_enterprise.actions.Ping.SpyCloudSDK",
        return_value=spycloud_sdk,
    ):
        yield

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from core.base_action import BaseAction
from core.opencti_client.client import OpenCTIClient

FAKE_OPENCTI_URL = "https://opencti.example.com"
FAKE_OPENCTI_TOKEN = "secret-token"


class ConcreteAction(BaseAction):
    def _init_api_clients(self) -> OpenCTIClient:
        return super()._init_api_clients()

    def _perform_action(self, _=None) -> None:
        pass


@pytest.fixture(autouse=True)
def mock_soar_action(monkeypatch) -> MagicMock:
    mock_soar = MagicMock()
    mock_soar.get_configuration.return_value = {
        "URL": FAKE_OPENCTI_URL,
        "API Token": FAKE_OPENCTI_TOKEN,
        "Verify SSL": True,
    }

    monkeypatch.setattr(
        "TIPCommon.base.action.base_action.create_soar_action",
        lambda: mock_soar,
    )

    return mock_soar


@pytest.fixture(autouse=True)
def mock_pycti_client(monkeypatch) -> MagicMock:
    mock_pycti_client = MagicMock(return_value=MagicMock())

    monkeypatch.setattr("core.opencti_client.client.OpenCTIApiClient", mock_pycti_client)

    return mock_pycti_client


class TestBaseActionIsAbstract:
    def test_cannot_instantiate_base_action_directly(self):
        with pytest.raises(TypeError):
            BaseAction("some-script")  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self):
        assert isinstance(ConcreteAction("Test Action"), BaseAction)


class TestApiClient:
    @pytest.fixture
    def action(self) -> ConcreteAction:
        return ConcreteAction("Test Action")

    def test_init_api_clients_returns_opencti_client(self, action):
        client = action._init_api_clients()

        assert isinstance(client, OpenCTIClient)

    def test_api_client_property_returns_opencti_client(self, action):
        # Set `_api_client` attribute as it would be done in `Action.run`
        action._api_client = action._init_api_clients()

        assert isinstance(action.api_client, OpenCTIClient)

    def test_api_client_uses_url_and_token_from_config(self, action, mock_pycti_client):
        action._init_api_clients()

        mock_pycti_client.assert_called_once_with(
            FAKE_OPENCTI_URL,
            FAKE_OPENCTI_TOKEN,
            ssl_verify=True,
        )

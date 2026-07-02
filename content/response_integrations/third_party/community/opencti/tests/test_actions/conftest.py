from __future__ import annotations

from unittest.mock import MagicMock

import pytest

FAKE_OPENCTI_URL = "https://opencti.example.com"
FAKE_OPENCTI_TOKEN = "secret-token"


@pytest.fixture(autouse=True)
def mock_soar_action(monkeypatch) -> MagicMock:
    mock_soar = MagicMock()
    mock_soar.get_configuration.return_value = {
        "URL": FAKE_OPENCTI_URL,
        "API Token": FAKE_OPENCTI_TOKEN,
        "Verify SSL": True,
    }
    mock_soar.parameters = {}
    mock_soar.target_entities = []

    monkeypatch.setattr(
        "TIPCommon.base.action.base_action.create_soar_action",
        lambda: mock_soar,
    )

    return mock_soar


@pytest.fixture
def mock_soar_enrich_action(monkeypatch) -> MagicMock:
    """Mock SiemplifyAction for enrich actions based on local_action_runner setup."""
    mock_soar = MagicMock()
    mock_soar.get_configuration.return_value = {
        "URL": FAKE_OPENCTI_URL,
        "API Token": FAKE_OPENCTI_TOKEN,
        "Verify SSL": True,
    }
    mock_soar.parameters = {}
    mock_soar.target_entities = []
    mock_soar.action_definition_name = "Test Action"
    mock_soar.execution_deadline_unix_time_ms = 2**63 - 1

    monkeypatch.setattr(
        "TIPCommon.base.action.base_action.create_soar_action",
        lambda: mock_soar,
    )

    return mock_soar


@pytest.fixture(autouse=True)
def mock_api_client(monkeypatch) -> MagicMock:
    """Mock OpenCTIClient at the base_action import level.

    Returns the mock instance so tests can configure return values directly
    (e.g. mock_api_client.create_incident.return_value = ...).
    """
    mock_client = MagicMock()
    mock_class = MagicMock(return_value=mock_client)
    monkeypatch.setattr("core.base_action.OpenCTIClient", mock_class)
    return mock_client

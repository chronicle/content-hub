from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest
import soar_sdk  # noqa: F401

sys.stdout = sys.__stdout__


@pytest.fixture(autouse=True)
def mock_siemplify(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock SiemplifyAction for all actions to prevent sys.argv crashes.

    Args:
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        MagicMock: mock siemplify object.
    """
    mock_api: MagicMock = MagicMock()
    mock_api.LOGGER = MagicMock()
    mock_api.result = MagicMock()
    mock_api.end = MagicMock()

    # List of actions to mock
    actions: list[str] = [
        "Ping",
        "ListAlerts",
        "AddEntitiesToURLList",
        "AllowFile",
        "BlockFile",
        "DeployURLListChanges",
        "DownloadFile",
        "ListClients",
        "ListEvents",
        "ListQuarantinedFiles",
    ]

    for action in actions:
        try:
            monkeypatch.setattr(
                f"netskope.actions.{action}.SiemplifyAction",
                MagicMock(return_value=mock_api, LOGGER=mock_api.LOGGER),
            )
        except (AttributeError, ModuleNotFoundError):
            pass

    return mock_api

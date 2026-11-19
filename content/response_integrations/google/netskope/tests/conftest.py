from __future__ import annotations
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_siemplify(monkeypatch) -> MagicMock:
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
                f"Integrations.Netskope.ActionsScripts.{action}.SiemplifyAction",
                MagicMock(return_value=mock_api, LOGGER=mock_api.LOGGER),
            )
        except AttributeError:
            # If the module hasn't been imported yet or doesn't exist, we
            # might get an error if we try to patch it directly like this
            # without it being loaded.
            # But pytest runs from root, so it might work if it's imported in the test.
            # Usually, monkeypatch can patch modules if you give the full path string.
            pass

    return mock_api

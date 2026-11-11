from __future__ import annotations

from typing import Any
import json
import pytest
from connect_wise.core import ConnectWiseManager


@pytest.fixture(name="load_config")
def fixture_load_config() -> dict[str, Any]:
    """Load integration configuration from config.json file and return it as dict.

    Returns:
        dict[str, Any]: dictionary object for create auth and api params object.
    """
    integration_config = {}
    with open("config.json", "r", encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    integration_config["company_url"] = config["Api Root"]
    integration_config["company_name"] = config["Company Name"]
    integration_config["public_key"] = config["Public Key"]
    integration_config["private_key"] = config["Private Key"]
    integration_config["client_id"] = config["Client Id"]
    return integration_config


@pytest.fixture(name="api_manager")
def fixture_manager(
    load_config: dict[str, Any],
) -> ConnectWiseManager.ConnectWiseManager:
    return ConnectWiseManager.ConnectWiseManager(**load_config)

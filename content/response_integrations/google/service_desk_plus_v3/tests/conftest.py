from __future__ import annotations
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout
import json
import os

import pytest
import requests

from soar_sdk.SiemplifyAction import SiemplifyAction

from service_desk_plus_v3.core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3
from service_desk_plus_v3.tests.common import CONFIG
from service_desk_plus_v3.tests.core.product import ServiceDeskPlusV3
from service_desk_plus_v3.tests.core.session import ServiceDeskPlusV3Session

@pytest.fixture(scope="module")
def mock_data() -> dict:
    """Load mock data from mock_data.json."""
    mock_data_path = os.path.join(os.path.dirname(__file__), "mock_data.json")
    with open(mock_data_path, encoding="utf-8") as f:
        return json.load(f)

class MockAlert:
    def __init__(self):
        self.external_id = "mock_external_id"
        self.identifier = "mock_identifier"

@pytest.fixture(autouse=True)
def mock_siemplify(monkeypatch):
    monkeypatch.setattr(SiemplifyAction, "current_alert", property(lambda self: MockAlert()))
    monkeypatch.setattr(SiemplifyAction, "add_tag", lambda *args, **kwargs: None)
    monkeypatch.setattr(SiemplifyAction, "update_alerts_additional_data", lambda *args, **kwargs: None)

@pytest.fixture(name="product")
def service_desk_plus_v3_product() -> ServiceDeskPlusV3:
    return ServiceDeskPlusV3()

@pytest.fixture(autouse=True)
def script_session(monkeypatch, product) -> ServiceDeskPlusV3Session:
    session = ServiceDeskPlusV3Session(product)
    """Mock ServiceDeskPlusV3 scripts' session."""

    monkeypatch.setattr(requests.Session, "get", handle_get)
    monkeypatch.setattr(requests.Session, "post", handle_post)
    return session

@pytest.fixture(name="manager")
def service_desk_plus_v3_manager() -> ServiceDeskPlusManagerV3:
    return ServiceDeskPlusManagerV3(CONFIG["Api Root"], CONFIG["Api Key"], verify_ssl=False)

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session

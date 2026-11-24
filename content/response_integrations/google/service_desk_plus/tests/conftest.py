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
import xmltodict
from soar_sdk.SiemplifyAction import SiemplifyAction
from service_desk_plus.core.ServiceDeskPlusManager import ServiceDeskPlusManager
from service_desk_plus.tests.common import CONFIG
from service_desk_plus.tests.core.product import ServiceDeskPlus
from service_desk_plus.tests.core.session import ServiceDeskPlusSession

class XmlMockResponse:
    def __init__(self, original_resp):
        self.original_resp = original_resp
        self.status_code = original_resp.status_code

    @property
    def text(self):
        try:
            # MockResponse converts dict to JSON string in .text
            data = json.loads(self.original_resp.text)
            if isinstance(data, dict):
                xml_str = xmltodict.unparse(data)
                print(f"DEBUG: XmlMockResponse.text converted JSON to XML: {xml_str}")
                return xml_str
        except json.JSONDecodeError:
            pass

        print(f"DEBUG: XmlMockResponse.text returning raw: {self.original_resp.text}")
        return self.original_resp.text

    def json(self):
        return self.original_resp.json()


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
def service_desk_plus_product() -> ServiceDeskPlus:
    return ServiceDeskPlus()

@pytest.fixture(autouse=True)
def script_session(monkeypatch, product) -> ServiceDeskPlusSession:
    session = ServiceDeskPlusSession(product)
    """Mock ServiceDeskPlus scripts' session."""

    monkeypatch.setattr(requests, "get", handle_get)
    monkeypatch.setattr(requests, "post", handle_post)
    return session

@pytest.fixture(name="manager")
def service_desk_plus_manager() -> ServiceDeskPlusManager:
    return ServiceDeskPlusManager(CONFIG["Api Root"], CONFIG["Api Key"])

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session

# Copyright 2026 Google LLC

from __future__ import annotations
from collections import namedtuple
import json
import os
import pathlib
import pkgutil
import pytest
import soar_sdk

import importlib
import pkgutil
import sys

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

# Save original stdout in case soar_sdk imports hijack it (Siemplify.py calls SiemplifyUtils.override_stdout)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout
import sys

pytest_plugins = ("integration_testing.conftest",)

# Unify the soar_sdk namespace with the flat namespace for mocks

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

# Add parent directory and integration directory to sys.path to support internal module resolution
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

int_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if int_dir not in sys.path:
    sys.path.insert(0, int_dir)

from urllib.parse import urlencode

# Provide integration_testing fixtures
@pytest.fixture
def opensearch_product():
    from open_search.tests.core.product import OpenSearchProduct
    yield OpenSearchProduct()

CONNECTION_PERFORM_REQUEST_PATH = (
    "opensearchpy.connection.Urllib3HttpConnection.perform_request"
)

OpenSearchConfigParameters = namedtuple(
    "OpenSearchConfigParameters",
    [
        "server",
        "ca_certificate_file",
        "verify_ssl",
        "authenticate",
        "username",
        "password",
        "api_token",
    ],
)

def read_config(config_path: str):
    """
    Reads and parses the integration configuration from a JSON file.

    Args:
        config_path: The path to the configuration file.

    Returns:
        An `OpenSearchConfigParameters` object with the parsed configuration.
    """
    with open(config_path, encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    return OpenSearchConfigParameters(
        server=config.get("Server Address"),
        ca_certificate_file=config.get("CA Certificate File"),
        verify_ssl=config.get("Verify SSL") == "True",
        authenticate=config.get("Authenticate") == "True",
        username=config.get("Username"),
        password=config.get("Password"),
        api_token=config.get("API/Jwt Tokens"),
    )

@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch, opensearch_product  # pylint: disable=redefined-outer-name
):
    """
    A pytest fixture that creates and yields a mock `OpenSearchSession`.

    This fixture automatically patches the `perform_request` method of the
    `Urllib3HttpConnection` to intercept HTTP requests and route them to the
    mock session. This allows for testing of the OpenSearch integration
    without making actual network calls.

    Args:
        monkeypatch: The pytest `monkeypatch` fixture.
        opensearch_product: The `OpenSearchProduct` fixture.

    Yields:
        An instance of `OpenSearchSession` for use in tests.
    """
    from open_search.tests.core.session import OpenSearchSession
    session = OpenSearchSession(opensearch_product)

    def bridge_perform_request(
        self, method, url, params=None, body=None, headers=None, **kwargs
    ):
        full_url = f"{self.scheme}://{self.host}:{self.port}{url}"
        if params:
            full_url += f"?{urlencode(params)}"

        request_kwargs = kwargs
        if body:
            request_kwargs["json"] = body
        if params:
            request_kwargs["params"] = params
        if headers:
            request_kwargs["headers"] = headers

        response = session.request(method, full_url, **request_kwargs)
        return response.status_code, response.headers, response.text

    monkeypatch.setattr(CONNECTION_PERFORM_REQUEST_PATH, bridge_perform_request)
    yield session

@pytest.fixture
def manager():
    from open_search.core.os_client import OpenSearchManager
    from integration_testing.logger import Logger
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = read_config(config_path)
    return OpenSearchManager(integration_parameters=config, logger=Logger())

def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """
    Add a filterwarnings marker to all tests to suppress specific warnings.
    """
    for item in items:
        # Suppress opensearch-py UserWarning for insecure connections
        item.add_marker(
            pytest.mark.filterwarnings(
                "ignore:Connecting to .* using SSL with verify_certs=False "
                "is insecure.:UserWarning"
            )
        )
        # Suppress the underlying urllib3 InsecureRequestWarning
        item.add_marker(
            pytest.mark.filterwarnings(
                "ignore::urllib3.exceptions.InsecureRequestWarning"
            )
        )

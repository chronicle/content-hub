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
from collections import namedtuple
from urllib.parse import urlencode

import pytest

from open_search.core.os_client import OpenSearchManager
from open_search.tests.core.product import OpenSearchProduct
from open_search.tests.core.session import OpenSearchSession
from integration_testing.logger import Logger

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


def read_config(config_path: str) -> OpenSearchConfigParameters:
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


@pytest.fixture
def opensearch_product() -> OpenSearchProduct:
    yield OpenSearchProduct()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch, opensearch_product: OpenSearchProduct  # pylint: disable=redefined-outer-name
) -> OpenSearchSession:
    session = OpenSearchSession(opensearch_product)
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

    monkeypatch.setattr(CONNECTION_PERFORM_REQUEST_PATH, bridge_perform_request)
    yield session


@pytest.fixture
def manager() -> OpenSearchManager:
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

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session

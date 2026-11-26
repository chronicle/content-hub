# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import sys
import os
import soar_sdk
import json
from collections import namedtuple
from urllib.parse import urlencode
import pytest
import integration_testing.common as integration_testing_common
from open_search.core.os_client import OpenSearchManager
from open_search.tests.core.product import OpenSearchProduct
from open_search.tests.core.session import OpenSearchSession
from integration_testing.logger import Logger

pytest_plugins = ("integration_testing.conftest",)

sdk_dir = soar_sdk.__path__[0]

if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

CONNECTION_PERFORM_REQUEST_PATH = (
    "opensearchpy.connection.Urllib3HttpConnection.perform_request"
)

YAML_PARAM_TYPE_MAP = {
    "boolean": 0,
    "integer": 1,
    "string": 2,
    "password": 3,
    "ip": 4,
    "host": 5,
    "url": 6,
    "domain": 7,
    "email": 8,
}

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
    session = OpenSearchSession(opensearch_product)
    original_get_def_file_content = integration_testing_common.get_def_file_content

    def normalized_get_def_file_content(def_file_path):
        data = original_get_def_file_content(def_file_path)
        if isinstance(data, dict) and "Parameters" not in data and isinstance(data.get("parameters"), list):
            data["Parameters"] = [
                {
                    "Name": param["name"],
                    "Type": YAML_PARAM_TYPE_MAP.get(str(param.get("type", "string")).lower(), 2),
                    "DefaultValue": param.get("default_value", ""),
                    "IsMandatory": param.get("is_mandatory", False),
                    "Mode": 2 if param.get("mode") == "script" else 0,
                }
                for param in data["parameters"]
            ]
        return data

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

    monkeypatch.setattr(
        integration_testing_common,
        "get_def_file_content",
        normalized_get_def_file_content,
    )
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

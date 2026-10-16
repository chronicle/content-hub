import json
import os
import site
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

for p in site.getsitepackages():
    soar_sdk_path = os.path.join(p, "soar_sdk")
    if os.path.exists(soar_sdk_path):
        sys.path.insert(0, soar_sdk_path)

from sap_erp.core.sap_erp_manager import SapErpManager  # noqa: E402


@pytest.fixture(autouse=True)
def mock_siemplify():
    """SiemplifyAction reads sys.argv/stdin on init; replace it with a mock."""
    with patch("TIPCommon.base.action.base_action.create_soar_action") as mock_create:
        mock_create.return_value = MagicMock()
        yield


def build_response(status_code=200, json_body=None, text=None):
    """Build a real requests.Response so .ok/.json()/.text behave naturally."""
    response = requests.Response()
    response.status_code = status_code
    if json_body is not None:
        response._content = json.dumps(json_body).encode("utf-8")
    else:
        response._content = (text or "").encode("utf-8")
    response.encoding = "utf-8"
    return response


@pytest.fixture
def make_response():
    return build_response


@pytest.fixture
def manager():
    """Mocked SapErpManager that keeps the real static error extractor."""
    mock_manager = MagicMock(spec=SapErpManager)
    mock_manager.extract_error_detail.side_effect = SapErpManager.extract_error_detail
    return mock_manager

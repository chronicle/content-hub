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
from collections.abc import Iterator
import json
import copy
import tempfile
from contextlib import contextmanager
from typing import Any

import pytest

from TIPCommon.base.utils import CreateSession
from sentinel_one_v2.tests.common import MOCK_CLOUD_ALERT, TEST_ALERT_ID
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from sentinel_one_v2.tests.core.session import MockJobCase
from integration_testing.common import use_live_api


@pytest.fixture
def temp_json_file():
    """Creates a temp json file for tests"""

    @contextmanager
    def _temp_json_file(ids: dict[str, Any]):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(ids, temp_file)
            temp_file.flush()
            yield temp_file

    return _temp_json_file


@pytest.fixture
def sentinel_one_v2() -> Iterator[SentinelOneV2]:
    yield SentinelOneV2()

# pylint: disable=redefined-outer-name
@pytest.fixture
def mock_alert(sentinel_one_v2: SentinelOneV2) -> None:
    """Fixture to add a mock cloud alert to the product."""
    alert_data = copy.deepcopy(MOCK_CLOUD_ALERT)
    sentinel_one_v2.add_cloud_detection_alert(TEST_ALERT_ID, alert_data)


# pylint: disable=redefined-outer-name
@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    sentinel_one_v2: SentinelOneV2,
) -> Iterator[SentinelOneV2Session]:
    session = Iterator[SentinelOneV2Session](sentinel_one_v2)
    """
    Mock SentinelOneV2 scripts'
    session and get back an object to view request history
    """

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
    yield session

# pylint: disable=redefined-outer-name
@pytest.fixture
def _script_session(script_session: SentinelOneV2Session) -> SentinelOneV2Session:
    """Alias for script_session, used by tests that discard the session object."""
    return script_session


# pylint: disable=redefined-outer-name
@pytest.fixture
def mock_job_case() -> Iterator[MockJobCase]:
    """Standard native SIEMPLIFY JobCase object injector."""
    yield MockJobCase

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session

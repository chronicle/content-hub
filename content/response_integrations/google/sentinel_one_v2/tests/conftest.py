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

import copy
import importlib
import json
import pkgutil
import sys
from contextlib import contextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
import soar_sdk

pytest_plugins = ("integration_testing.conftest",)

sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

from integration_testing.common import use_live_api  # noqa: E402
from TIPCommon.base.utils import CreateSession  # noqa: E402

from sentinel_one_v2.tests.common import MOCK_CLOUD_ALERT, TEST_ALERT_ID  # noqa: E402
from sentinel_one_v2.tests.core.product import SentinelOneV2  # noqa: E402
from sentinel_one_v2.tests.core.session import (  # noqa: E402
    MockJobCase,
    SentinelOneV2Session,
)

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    from TIPCommon.types import SingleJson


@pytest.fixture
def temp_json_file(
    tmp_path: pathlib.Path,
) -> Callable[[SingleJson], AbstractContextManager[SimpleNamespace]]:
    """Create a closed temporary JSON file under tmp_path for cross-platform file reads."""

    @contextmanager
    def _temp_json_file(ids: SingleJson) -> Iterator[SimpleNamespace]:
        file_path = tmp_path / "ids.json"
        file_path.write_text(json.dumps(ids), encoding="utf-8")
        yield SimpleNamespace(name=str(file_path))

    return _temp_json_file


@pytest.fixture
def sentinel_one_v2() -> Iterator[SentinelOneV2]:
    """Yield a fresh mock SentinelOneV2 product state."""
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
    """Mock SentinelOneV2 scripts' session and inspect request history."""
    session = SentinelOneV2Session(sentinel_one_v2)
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
def mock_job_case() -> Iterator[type[MockJobCase]]:
    """Standard native SIEMPLIFY JobCase object injector."""
    yield MockJobCase


_YAML_PARAM_TYPES: dict[str, int] = {
    "boolean": 0,
    "integer": 1,
    "string": 2,
    "password": 3,
}


@pytest.fixture(autouse=True)
def _normalize_yaml_def_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Adapt restructured lowercase YAML parameters to integration_testing schema."""
    import integration_testing.common as it_common

    orig_get_def = it_common.get_def_file_content

    def _wrapped_get_def(def_file_path: str | object | None) -> SingleJson:
        content = orig_get_def(def_file_path)
        if isinstance(content, dict) and "parameters" in content and "Parameters" not in content:
            content = dict(content)
            content["Parameters"] = [
                {
                    "Name": p["name"],
                    "Type": _YAML_PARAM_TYPES.get(str(p.get("type", "string")).lower(), 2),
                    "DefaultValue": str(p.get("default_value", "")),
                    "IsMandatory": bool(p.get("is_mandatory", False)),
                    "Mode": 0,
                }
                for p in content["parameters"]
            ]
        return content

    monkeypatch.setattr(it_common, "get_def_file_content", _wrapped_get_def)



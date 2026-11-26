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

"""Pytest fixtures for GoogleCloudCompute action tests.

Key responsibilities:
- Patch TIPCommon 2.x Action base class to support TIPCommon 1.x method names used
  by the production GoogleCloudCompute integration code.
- Patch google.auth so that no real OAuth token exchange occurs.
- Wire GoogleCloudComputeSession (MockSession subclass) into AuthorizedSession
  so every HTTP call is intercepted and routed through the fake product.
- Expose the ``compute_product`` fixture so individual tests can prime canned
  responses and configure failure modes.

# ISSUE FINDER: TIPCommon version mismatch
# ===========================================
# The GoogleCloudCompute production integration was written against TIPCommon 1.1.5.2
# (see Integrations/GoogleCloudCompute/requirements.txt: tipcommon==1.1.5.2).
#
# TIPCommon 1.x Action base class:
#   - Abstract method: _init_managers() -> manager  (not _init_api_clients)
#   - Param extraction: _extract_parameters()       (not _extract_action_parameters)
#   - run() calls: manager = self._init_managers()
#                  self._perform_action(manager, entity)
#   - self.is_first_run is a plain instance attribute (writable)
#
# TIPCommon 2.x Action base class (installed in test venv: 2.3.7):
#   - Abstract method: _init_api_clients() -> Contains[ApiClient]
#   - Param extraction: _extract_action_parameters() (nativemethod)
#   - run() calls: self._init_api_clients()
#                  self._perform_action(current_entity)   # manager not passed!
#   - self.is_first_run is a read-only @property (no setter!)
#
# Patches applied here (4 total):
#   1. _init_api_clients: concrete shim delegating to _init_managers().
#   2. _extract_action_parameters: delegates to _extract_parameters().
#   3. _Action__no_entities_action + _Action__entities_main_loop: wrap
#      perform_action_fn to inject manager as first arg (1.x call convention).
#   4. is_first_run: property replaced with one that has a setter.
"""
from __future__ import annotations

import contextlib
import importlib
import json
import pathlib
import pkgutil
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import soar_sdk

_sdk_dir = soar_sdk.__path__[0]
if _sdk_dir not in sys.path:
    sys.path.insert(0, _sdk_dir)
_original_stdout = sys.stdout
for _, _mod_name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    with contextlib.suppress(Exception):
        _flat_mod = importlib.import_module(_mod_name)
        sys.modules[f"soar_sdk.{_mod_name}"] = _flat_mod
        setattr(soar_sdk, _mod_name, _flat_mod)
sys.stdout = _original_stdout

import cryptography.hazmat.primitives.serialization  # noqa: E402
import google.auth.transport.requests  # noqa: E402
import pytest  # noqa: E402
from integration_testing.common import use_live_api  # noqa: E402
from pytest_factoryboy import register  # noqa: E402
from soar_sdk import Siemplify  # noqa: E402
from TIPCommon.base.action import Action  # noqa: E402

from google_cloud_compute.core import GoogleCloudComputeManager as compute_manager_module
from google_cloud_compute.core.GoogleCloudComputeManager import GoogleCloudComputeManager
from google_cloud_compute.tests import factories
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import GoogleCloudComputeSession

if TYPE_CHECKING:
    from collections.abc import Iterator

    import pytest_mock

pytest_plugins = ("integration_testing.conftest",)

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"

# Shim 4: add setter to is_first_run property
_is_first_run_prop = property(
    fget=lambda self: self._is_first_run,
    fset=lambda self, value: setattr(self, "_is_first_run", value),
)
Action.is_first_run = _is_first_run_prop  # type: ignore[method-assign]

register(factories.OperationFactory)
register(factories.FirewallRuleFactory)
register(factories.PatchJobFactory)


@pytest.fixture
def compute_product() -> GoogleCloudCompute:
    """Provide the fake GCP Compute product instance for a test."""
    return GoogleCloudCompute()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    compute_product: GoogleCloudCompute,
) -> Iterator[GoogleCloudComputeSession]:
    """Intercept all HTTP traffic for GoogleCloudCompute scripts."""
    session = GoogleCloudComputeSession(compute_product)

    if not use_live_api():
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *_, **__: session,
        )
        monkeypatch.setattr(
            compute_manager_module,
            "AuthorizedSession",
            lambda *_, **__: session,
        )
        monkeypatch.setattr(
            compute_manager_module,
            "build_credentials_from_sa",
            lambda **__: MagicMock(),
        )
        monkeypatch.setattr(
            compute_manager_module,
            "retrieve_project_id",
            lambda *_, **__: "test-project",
        )
        monkeypatch.setattr(
            compute_manager_module,
            "get_workload_sa_email",
            lambda default_sa="": default_sa or "default@domain.com",
        )
        monkeypatch.setattr(
            cryptography.hazmat.primitives.serialization,
            "load_pem_private_key",
            lambda *_, **__: "fake_private_key",
        )
        monkeypatch.setattr(
            GoogleCloudComputeManager,
            "prepare_auth_request",
            staticmethod(lambda *_, **__: MagicMock()),
        )
    yield session


@pytest.fixture(autouse=True)
def _stub_siemplify_update_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out the platform entity-update call."""
    monkeypatch.setattr(Siemplify.Siemplify, "update_entities", lambda *_, **__: None)


@pytest.fixture
def _script_session(script_session: GoogleCloudComputeSession) -> GoogleCloudComputeSession:
    """Alias for script_session."""
    return script_session


@pytest.fixture
def _compute_product(compute_product: GoogleCloudCompute) -> GoogleCloudCompute:
    """Alias for compute_product."""
    return compute_product


@pytest.fixture
def compute_manager(mocker: pytest_mock.MockerFixture) -> GoogleCloudComputeManager:
    """Provide a GoogleCloudComputeManager instance configured from tests/config.json."""
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    api_root = config["API Root"]

    mocker.patch.object(
        compute_manager_module,
        "build_credentials_from_sa",
        return_value=mocker.Mock(),
    )

    return GoogleCloudComputeManager(
        api_root=api_root,
        workload_identity_email="test-sa@gcloud.iam.com",
    )


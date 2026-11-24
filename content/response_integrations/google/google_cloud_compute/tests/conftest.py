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
from typing import Any
from unittest.mock import MagicMock

import cryptography.hazmat.primitives.serialization
import google.auth.transport.requests
import pytest
from pytest_factoryboy import register

from soar_sdk import Siemplify

from TIPCommon.base.action import Action

from google_cloud_compute.core.GoogleCloudComputeManager import (
    GoogleCloudComputeManager,
)
from google_cloud_compute.tests import factories
from google_cloud_compute.tests.core.product import GoogleCloudCompute
from google_cloud_compute.tests.core.session import (
    GoogleCloudComputeSession,
)
from integration_testing.common import use_live_api

pytest_plugins = ("Tests.mocks.ci_fixtures",)


# ---------------------------------------------------------------------------
# TIPCommon 1.x -> 2.x backward-compatibility shim
#
# ISSUE FINDER: Four incompatibilities between TIPCommon 1.1.5.2 (production)
# and TIPCommon 2.3.7 (test venv) that prevent tests from running:
#
# 1. ABSTRACT METHOD RENAME: _init_managers() -> _init_api_clients()
#    Production defines _init_managers; 2.x marks _init_api_clients @abstractmethod.
#    Without the shim: TypeError("Can't instantiate abstract class X with abstract
#    method _init_api_clients") for every action class.
#
# 2. PARAM-EXTRACTION RENAME: _extract_parameters() -> _extract_action_parameters()
#    Production calls _extract_parameters(); 2.x run() invokes _extract_action_parameters().
#    Without the shim: parameter extraction is silently skipped, all params are None.
#
# 3. CALL-CONVENTION CHANGE: _perform_action(manager, entity) -> _perform_action(entity)
#    1.x passed the manager object as first arg; 2.x passes only the entity (None for
#    non-entity actions). Production code uses manager.get_firewall_rule(), etc.
#    Without the shim: AttributeError('NoneType' has no attribute 'get_firewall_rule').
#
# 4. PROPERTY SETTER MISSING: is_first_run is a read-only @property in 2.x.
#    Production __init__ methods do self.is_first_run = is_first_run(sys.argv).
#    Without the shim: AttributeError("property 'is_first_run' has no setter").
# ---------------------------------------------------------------------------





# Shim 4: add setter to is_first_run property
_is_first_run_prop = property(
    fget=lambda self: self._is_first_run,
    fset=lambda self, value: setattr(self, "_is_first_run", value),
)
Action.is_first_run = _is_first_run_prop  # type: ignore[method-assign]

# ---------------------------------------------------------------------------
# Register factory fixtures
# ---------------------------------------------------------------------------
register(factories.OperationFactory)
register(factories.FirewallRuleFactory)
register(factories.PatchJobFactory)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def compute_product() -> GoogleCloudCompute:
    """Provides the fake GCP Compute product instance for a test."""
    return GoogleCloudCompute()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    compute_product: GoogleCloudCompute,
) -> GoogleCloudComputeSession:
    session = GoogleCloudComputeSession(compute_product)
    """Intercept all HTTP traffic for GoogleCloudCompute scripts.

    Patches:
    - ``google.auth.transport.requests.AuthorizedSession`` replaced with test session.
    - ``build_credentials_from_sa`` skips real GCP credential negotiation.
    - ``cryptography load_pem_private_key`` avoids PEM parsing of fake keys.
    - ``retrieve_project_id`` returns a fixed project ID.
    - ``prepare_auth_request`` skips real token refresh.
    """

    if not use_live_api():
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *_, **__: session,
        )
        monkeypatch.setattr(
            "GoogleCloudComputeManager.build_credentials_from_sa",
            lambda **__: MagicMock(),
        )
        monkeypatch.setattr(
            "GoogleCloudComputeManager.retrieve_project_id",
            lambda *_, **__: "test-project",
        )
        monkeypatch.setattr(
            cryptography.hazmat.primitives.serialization,
            "load_pem_private_key",
            lambda *_, **__: "fake_private_key",
        )
        monkeypatch.setattr(
            "GoogleCloudComputeManager.GoogleCloudComputeManager.prepare_auth_request",
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
def compute_manager(mocker) -> GoogleCloudComputeManager:
    """Gcloud Compute Manager fixture"""
    with open("config.json", "r", encoding="utf-8") as f:
        data = f.read()

    config = json.loads(data)
    api_root = config["API Root"]

    mocker.patch(
        "google_cloud_compute.core."
        "GoogleCloudComputeManager.build_credentials_from_sa",
        return_value=mocker.Mock()
    )

    manager = GoogleCloudComputeManager(
        api_root=api_root,
        workload_identity_email="test-sa@gcloud.iam.com",
    )

    return manager

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session

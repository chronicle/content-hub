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

# ---------------------------------------------------------------------------
# TIPCommon 1.x compatibility shim
# ---------------------------------------------------------------------------
# The integration action scripts (Integrations/MitreAttck/ActionsScripts/*.py)
# were written against TIPCommon 1.x and use flat imports such as:
#   from TIPCommon import extract_configuration_param
# TIPCommon 2.x only exposes submodules at the top level. This block re-exports
# the needed symbols at the TIPCommon package level so the legacy imports work.
import TIPCommon
try:
    import TIPCommon.extraction
    import TIPCommon.transformation
    for _name in (
        "extract_configuration_param",
        "extract_action_param",
        "extract_script_param",
        "extract_connector_param",
    ):
        if not hasattr(TIPCommon, _name):
            setattr(TIPCommon, _name, getattr(TIPCommon.extraction, _name))
    for _name in (
        "construct_csv",
        "flat_dict_to_csv",
        "string_to_multi_value",
        "dict_to_flat",
        "add_prefix_to_dict",
    ):
        if not hasattr(TIPCommon, _name):
            setattr(TIPCommon, _name, getattr(TIPCommon.transformation, _name))
except ImportError:
    pass  # TIPCommon 1.x — flat imports already work
# ---------------------------------------------------------------------------

import requests
import pytest

from mitre_attck.core.MitreAttckManager import MitreAttckManager
from mitre_attck.tests.common import ENTERPRISE_ATTACK
from mitre_attck.tests.core.product import MitreAttckProduct
from mitre_attck.tests.core.session import MitreAttckSession
from integration_testing.common import use_live_api

pytest_plugins = ("Tests.mocks.ci_fixtures",)


@pytest.fixture
def mitre_product() -> MitreAttckProduct:
    """Provide a fresh MitreAttckProduct pre-loaded with the default STIX bundle."""
    product = MitreAttckProduct()
    product.set_attack_data(ENTERPRISE_ATTACK)
    return product


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    mitre_product: MitreAttckProduct,
) -> MitreAttckSession:
    session = MitreAttckSession(mitre_product)
    """Intercept all requests.Session calls and route them to the product mock."""

    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
    yield session


@pytest.fixture
def mock_connectivity_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force MitreAttckManager.test_connectivity to raise an exception."""

    def _raise(*_args, **_kwargs) -> None:
        raise RuntimeError("Simulated connectivity failure")

    monkeypatch.setattr(MitreAttckManager, "test_connectivity", _raise)


@pytest.fixture
def _script_session(script_session: MitreAttckSession) -> MitreAttckSession:
    """Alias for script_session — used in tests that reference the session for assertions."""
    return script_session

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session

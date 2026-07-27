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
import pathlib
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
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

# Set environment variables for SDK to use a temp folder instead of /opt/siemplify
os.environ['SIEMPLIFY_RUN_FOLDER'] = os.path.join(int_dir, '.venv', 'siemplify_run')
os.environ['SIEMPLIFY_LOGS_FOLDER'] = os.path.join(int_dir, '.venv', 'siemplify_logs')
os.makedirs(os.environ['SIEMPLIFY_RUN_FOLDER'], exist_ok=True)
os.makedirs(os.environ['SIEMPLIFY_LOGS_FOLDER'], exist_ok=True)
import pytest

from ..tests.core.session import MySQLSession
from ..core import MySQLManager


@pytest.fixture(autouse=True)
def mysql_session(monkeypatch: pytest.MonkeyPatch) -> MySQLSession:
    """Mock MySQL session connection"""
    session = MySQLSession()

    monkeypatch.setattr(
        MySQLManager.mysql.connector, "connect", lambda **kwargs: session
    )

    yield session


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

@pytest.fixture(autouse=True)
def enterprise_standardization_mocks(monkeypatch, script_session, request):

    # 2. Fix the descriptor bug for run_folder
    try:
        from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
        monkeypatch.setattr(SiemplifyConnectorExecution, "run_folder", property(lambda self: "/tmp/siemplify_run"))
        monkeypatch.setattr(SiemplifyConnectorExecution, "environment_field_name", "environment")
        
        # Monkeypatch GetEnvironmentCommonFactory to prevent crashes
        from EnvironmentCommon import GetEnvironmentCommonFactory
        class DummyEnvMgr:
            def get_environment(self, *args, **kwargs):
                return "Default Environment"
        GetEnvironmentCommonFactory.create_environment_manager = lambda *_, **__: DummyEnvMgr()
    except Exception:
        pass
        

    # 4. Patch CaseDetails.__init__ for missing arguments in integration-testing
    try:
        from TIPCommon.data_models import CaseDetails
        import inspect
        orig_case_init = CaseDetails.__init__
        def patched_case_init(self, *args, **kwargs):
            sig = inspect.signature(orig_case_init)
            bound = sig.bind_partial(self, *args, **kwargs)
            for name, param in sig.parameters.items():
                if name not in bound.arguments:
                    if param.default == inspect.Parameter.empty:
                        bound.arguments[name] = None
            orig_case_init(*bound.args, **bound.kwargs)
        monkeypatch.setattr(CaseDetails, "__init__", patched_case_init)
    except Exception:
        pass

    return script_session

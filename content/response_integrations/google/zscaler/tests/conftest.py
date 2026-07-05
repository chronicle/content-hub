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
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import soar_sdk
# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon
sdk_dir = os.path.dirname(soar_sdk.__file__)
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


import dataclasses
import json
import pathlib
import auth
from typing import Any, Generator
from unittest.mock import MagicMock
from TIPCommon.base.utils import CreateSession
from SiemplifyBase import SiemplifyBase

import pytest

import zscalerManager

import base_action
from zscaler.core.data_models import IntegrationParameters
from zscaler.tests.core.session import ZscalerSession
from zscaler.tests.core.zscaler import Zscaler

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@dataclasses.dataclass
class LegacyActionOutput:
    """
    Local replacement for MockActionOutput.
    Captures the output from siemplify.end().
    """

    output_message: str | None = None
    result_value: bool | str | None = None
    status: str | None = None
    is_success: bool = False

    def set_output(self, *args: Any, **kwargs: Any) -> None:
        """Mock implementation of siemplify.end()"""
        if args:
            self.output_message = args[0]
            self.result_value = args[1] if len(args) > 1 else False
            self.status = args[2] if len(args) > 2 else "COMPLETED"
        else:
            self.output_message = kwargs.get("output_message") or kwargs.get("message")
            self.result_value = kwargs.get("result_value")
            self.status = kwargs.get("status")

        self.is_success = self.result_value in [True, "true"]


@pytest.fixture
def action_output() -> LegacyActionOutput:
    """Fixture providing an instance of LegacyActionOutput."""
    yield LegacyActionOutput()


@dataclasses.dataclass
class LegacyJsonResults:
    """
    Local replacement for MockJsonResults.
    Captures data from siemplify.result.add_result_json().
    """

    json_results_str: str = "[]"

    def set_json_results(self, json_data: list | dict) -> None:
        """Mock implementation of siemplify.result.add_result_json()"""
        self.json_results_str = json.dumps(json_data)


@pytest.fixture
def json_results() -> LegacyJsonResults:
    """Fixture providing an instance of LegacyJsonResults."""
    yield LegacyJsonResults()


@pytest.fixture(autouse=True)
# pylint: disable=redefined-outer-name
def mock_siemplify(
    monkeypatch: pytest.MonkeyPatch,
    action_output: LegacyActionOutput,
    json_results: LegacyJsonResults,
) -> MagicMock:
    """
    (autouse=True)
    Fully mocks the SiemplifyAction object for legacy scripts
    that import it directly.
    """
    mock_api = MagicMock()
    mock_api.LOGGER = MagicMock()

    mock_api.result = MagicMock()
    mock_api.result.add_result_json.side_effect = json_results.set_json_results
    mock_api.result.add_entity_table = MagicMock()

    mock_api.get_configuration.return_value = CONFIG
    mock_api.target_entities = []  # Default, tests can override
    mock_api.end.side_effect = action_output.set_output
    mock_api.execution_deadline_unix_time_ms = 2000000000000  # Year 2033

    try:
        monkeypatch.setattr(
            "zscaler.actions.AddToWhitelist.SiemplifyAction",
            lambda: mock_api,
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "zscaler.actions.AddToBlacklist.SiemplifyAction",
            lambda: mock_api,
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "zscaler.actions.LookupEntity.SiemplifyAction",
            lambda: mock_api,
        )
    except AttributeError:
        pass

    def mock_extract_param(
        siemplify: Any,
        provider_name: str,
        **kwargs,
    ) -> Any:
        """
        Mock implementation of extract_configuration_param
        that respects is_mandatory and default_value.
        """
        _ = siemplify
        _ = provider_name
        param_name = kwargs.get("param_name")
        is_mandatory = kwargs.get("is_mandatory", False)
        default_value = kwargs.get("default_value")

        if default_value is not None:
            return CONFIG.get(param_name, default_value)
        if is_mandatory:
            return CONFIG[param_name]
        return CONFIG.get(param_name)

    try:
        monkeypatch.setattr(
            "zscaler.actions.LookupEntity."
            "extract_configuration_param",
            mock_extract_param,
        )
    except AttributeError:
        pass

    monkeypatch.setattr(
        "TIPCommon.base.action.base_action.create_soar_action",
        lambda: mock_api,
    )

    yield mock_api


@pytest.fixture
def mock_data() -> dict[str, Any]:
    """
    Loads mock API response data from the JSON file.
    """
    mock_data_path = pathlib.Path(__file__).parent / "mock_data.json"
    return json.loads(mock_data_path.read_text(encoding="utf-8"))


@pytest.fixture
def zscaler_product() -> Zscaler:
    """
    Provides an instance of the mock Zscaler product (our mock database).
    """
    yield Zscaler()


@pytest.fixture(autouse=True)
def script_session(  # pylint: disable=redefined-outer-name
    monkeypatch: pytest.MonkeyPatch,
    zscaler_product: Zscaler,
    mock_data: dict[str, Any],
) -> Generator[ZscalerSession, None, None]:
    """
    (autouse=True)
    The core fixture that patches the requests.Session used by ZscalerManager.
    """
    zscaler_product.mock_data = mock_data
    session = ZscalerSession(zscaler_product)

    monkeypatch.setattr(
        base_action,
        "build_auth_params",
        lambda soar_sdk_object: IntegrationParameters(
            api_root="https://admin.zscalertwo.net",
            login_id="dummy@test.com",
            api_key="dummy_key",
            password="dummy_password",
            verify_ssl=False,
        ),
    )

    monkeypatch.setattr(CreateSession, "create_session", lambda *_, **__: session)
    monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    monkeypatch.setattr(SiemplifyBase, "_create_remote_session", lambda *_: session)
    monkeypatch.setattr(
        auth.AuthenticatedSession,
        "_obfuscate_api_key",
        lambda self, api_key, timestamp: zscaler_product.expected_api_key,
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
        
    # 3. Dynamic YAML shim to bypass .connectordef / mock JSON requirement
    import integration_testing.common
    from pathlib import Path
    orig_get_def = integration_testing.common.get_def_file_content
    def get_yaml_def_content(def_file_path):
        if not def_file_path:
            return {}
        path_str = str(def_file_path)
        int_dir = Path(__file__).parent.parent
        
        # INTERCEPT OLD JOB PATHS
        if "Integrations/" in path_str and "/Jobs/" in path_str:
            base_name = Path(path_str).name
            job_yaml = int_dir / "jobs" / base_name
            if job_yaml.exists():
                def_file_path = job_yaml
                path_str = str(job_yaml)

        # Convert legacy mock json paths into the real new yaml paths
        if path_str.endswith(".json") or path_str.endswith(".connectordef") or path_str.endswith(".yaml"):
            base_name = Path(path_str).stem
            # strip 'mock_' if it starts with it
            if base_name.startswith("mock_"):
                base_name = base_name[5:]
            
            # The real yaml is in the integration's connectors or jobs directory
            yaml_path = int_dir / "connectors" / f"{base_name}.yaml"
            if not yaml_path.exists():
                yaml_path = int_dir / "jobs" / f"{base_name}.yaml"
            if yaml_path.exists():
                import yaml
                with open(yaml_path, "r") as f:
                    data = yaml.safe_load(f)
                    
                    # Check if it has 'configuration' mapping (new mp yaml format)
                    if "configuration" in data:
                        parameters = []
                        for param_dict in data.get("configuration", []):
                            param_name = list(param_dict.keys())[0]
                            param_data = param_dict[param_name]
                            parameters.append({
                                "Name": param_name,
                                "Type": param_data.get("type", 0),
                                "IsMandatory": param_data.get("required", False),
                                "DefaultValue": param_data.get("default", "")
                            })
                        return {"Parameters": parameters}
                    
                    if "parameters" in data:
                        parameters = []
                        for param_dict in data.get("parameters", []):
                            parameters.append({
                                "Name": param_dict.get("name", ""),
                                "Type": param_dict.get("type", 0),
                                "IsMandatory": param_dict.get("is_mandatory", False),
                                "DefaultValue": param_dict.get("default_value", "")
                            })
                        return {"Parameters": parameters}
                    
                    # If it's old JSON structure in a YAML wrapper
                    if "Parameters" in data:
                        return data
        return orig_get_def(def_file_path)
        
    monkeypatch.setattr(integration_testing.common, "get_def_file_content", get_yaml_def_content)

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

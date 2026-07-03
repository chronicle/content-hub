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

import json
import os

import pytest
import requests

from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3
from ..tests.common import CONFIG
from ..tests.core.product import ServiceDeskPlusV3
from ..tests.core.session import ServiceDeskPlusV3Session

@pytest.fixture(scope="module")
def mock_data() -> dict:
    """Load mock data from mock_data.json."""
    mock_data_path = os.path.join(os.path.dirname(__file__), "mock_data.json")
    with open(mock_data_path, encoding="utf-8") as f:
        return json.load(f)

class MockAlert:
    def __init__(self):
        self.external_id = "mock_external_id"
        self.identifier = "mock_identifier"

@pytest.fixture(autouse=True)
def mock_siemplify(monkeypatch):
    monkeypatch.setattr(SiemplifyAction, "current_alert", property(lambda self: MockAlert()))
    monkeypatch.setattr(SiemplifyAction, "add_tag", lambda *args, **kwargs: None)
    monkeypatch.setattr(SiemplifyAction, "update_alerts_additional_data", lambda *args, **kwargs: None)

@pytest.fixture(name="product")
def service_desk_plus_v3_product() -> ServiceDeskPlusV3:
    return ServiceDeskPlusV3()

@pytest.fixture(autouse=True)
def script_session(monkeypatch, product) -> ServiceDeskPlusV3Session:
    """Mock ServiceDeskPlusV3 scripts' session."""
    session = ServiceDeskPlusV3Session(product)

    def handle_get(self_session, url, params=None, **kwargs):
        headers = dict(self_session.headers)
        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers

        mock_resp = session.get(url, params=params, **kwargs)
        real_resp = requests.Response()
        real_resp.status_code = mock_resp.status_code
        real_resp._content = json.dumps(mock_resp.json()).encode('utf-8')
        return real_resp

    def handle_post(self_session, url, params=None, data=None, **kwargs):
        headers = dict(self_session.headers)
        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers

        mock_resp = session.post(url, params=params, data=data, **kwargs)
        real_resp = requests.Response()
        real_resp.status_code = mock_resp.status_code
        real_resp._content = json.dumps(mock_resp.json()).encode('utf-8')
        return real_resp

    monkeypatch.setattr(requests.Session, "get", handle_get)
    monkeypatch.setattr(requests.Session, "post", handle_post)

    return session

@pytest.fixture(name="manager")
def service_desk_plus_v3_manager() -> ServiceDeskPlusManagerV3:
    return ServiceDeskPlusManagerV3(CONFIG["Api Root"], CONFIG["Api Key"], verify_ssl=False)


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

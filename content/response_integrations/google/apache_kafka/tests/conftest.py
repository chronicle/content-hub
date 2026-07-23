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


from typing import TYPE_CHECKING

import pytest

from ..actions.ping import Ping
from ..connectors.kafka_messages_connector import (
    KafkaMessagesConnector,
)
from ..core.kafka_manager import KafkaClient
from ..core import config_models

if TYPE_CHECKING:
    from typing import Any

    from pytest_mock import MockerFixture


@pytest.fixture()
def ping_action(mocker: MockerFixture) -> Ping:
    """Ping action fixture."""
    mocker.patch(
        "apache_kafka.actions.ping.create_kafka_client",
    )
    mocker.patch("TIPCommon.base.action.base_action.create_soar_action")
    mocker.patch("TIPCommon.base.action.base_action.create_logger")
    mocker.patch("TIPCommon.base.action.base_action.create_params_container")

    return Ping()


@pytest.fixture
def connector(mocker: MockerFixture) -> KafkaMessagesConnector:
    """Connector fixture"""
    mocker.patch(
        "TIPCommon.base.connector.base_connector.create_soar_connector",
    )
    return KafkaMessagesConnector()


@pytest.fixture
def mock_kafka_config(
    mocker: MockerFixture,
) -> config_models.KafkaConfigurationParameters:
    """Create a mock Kafka configuration object."""
    config = mocker.MagicMock(spec=config_models.KafkaConfigurationParameters)
    config.bootstrap_servers = "localhost:9092"
    config.sasl_username = None
    config.sasl_password = None
    config.ca_certificate = None
    config.client_certificate = None
    config.client_certificate_key = None
    config.client_certificate_key_password = None
    config.use_ssl = False
    config.use_sasl_ssl = False
    return config


@pytest.fixture
def mock_logger(mocker: MockerFixture) -> Any:
    """Create a mock logger object."""
    logger = mocker.MagicMock()
    return logger


@pytest.fixture
def kafka_client(
    mock_kafka_config: config_models.KafkaConfigurationParameters, # pylint: disable=redefined-outer-name
    mock_logger: Any,  # pylint: disable=redefined-outer-name
) -> KafkaClient:
    """Create a KafkaClient instance with mock configuration and logger."""
    return KafkaClient(kafka_config=mock_kafka_config, logger=mock_logger)


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

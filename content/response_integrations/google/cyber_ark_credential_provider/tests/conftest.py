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

import pathlib
import sys
from unittest.mock import MagicMock

for _mod in [
    "Siemplify",
    "SiemplifyAction",
    "SiemplifyLogger",
    "SiemplifyUtils",
    "SiemplifyBase",
    "SiemplifyConnectors",
    "SiemplifyJob",
    "SiemplifyAddressProvider",
    "SiemplifyDataModel",
    "SiemplifyConnectorsDataModel",
    "SiemplifyJobDataModel",
    "SiemplifyCaseDataModel",
    "SiemplifyVault",
    "SiemplifyVaultUtils",
    "ScriptResult",
    "OverflowManager",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "Integrations" / "CyberArkCredentialProvider" / 'jobs'))

from cyber_ark_credential_provider.core import constants
import pytest
from cyber_ark_credential_provider.core.credential_provider_manager import (
    CredentialProviderManager,
)
from pytest_mock import MockerFixture
from cyber_ark_credential_provider.tests.test_utils import read_config

from cyber_ark_credential_provider.core.datamodels import (
    ConfigurationParameters,
)

integration_params: ConfigurationParameters = read_config()


@pytest.fixture
def manager() -> CredentialProviderManager:
    """Fixture providing a CredentialProviderManager instance for tests.

    Returns:
        CredentialProviderManager: CredentialProviderManager instance.
    """
    return CredentialProviderManager(configuration_parameters=integration_params)


@pytest.fixture
def ssh_components_mock(mocker: MockerFixture):
    """Fixture to mock paramiko components."""
    mock_ssh_client_class = mocker.patch("paramiko.SSHClient")
    mock_rsa_key_class = mocker.patch("paramiko.RSAKey")
    mock_client_instance = mocker.MagicMock()
    mock_ssh_client_class.return_value = mock_client_instance
    mock_key_instance = mocker.MagicMock()
    mock_rsa_key_class.return_value = mock_key_instance

    mocker.patch("paramiko.Message.get_text", return_value="ssh-rsa")
    mocker.patch.dict(constants.KEY_CLASSES, {"ssh-rsa": mock_rsa_key_class})

    return mock_ssh_client_class, mock_client_instance, mock_key_instance


@pytest.fixture
def anyio_backend() -> str:
    """Force anyio to use asyncio backend for tests."""
    return "asyncio"

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session

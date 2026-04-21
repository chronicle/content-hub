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

import pytest
from pytest_mock import MockerFixture

from utils import read_config
from credential_provider_manager import (
    CredentialProviderManager,
)
from cyber_ark_credential_provider.core.datamodels import (
    IntegrationParameters
)
pytest_plugins = ("integration_testing.conftest",)


integration_params: IntegrationParameters = read_config()

@pytest.fixture
def manager() -> CredentialProviderManager:
    """Fixture providing a CredentialProviderManager instance for tests.

    Returns:
        CredentialProviderManager: CredentialProviderManager instance.
    """
    return CredentialProviderManager(integration_parameters=integration_params)


@pytest.fixture
def ssh_components_mock(mocker: MockerFixture):
    """Fixture to mock paramiko components."""
    mock_ssh_client_class = mocker.patch("paramiko.SSHClient")
    mock_rsa_key_class = mocker.patch("paramiko.RSAKey")
    mock_client_instance = mocker.MagicMock()
    mock_ssh_client_class.return_value = mock_client_instance
    mock_key_instance = mocker.MagicMock()
    mock_rsa_key_class.return_value = mock_key_instance

    return mock_ssh_client_class, mock_client_instance, mock_key_instance

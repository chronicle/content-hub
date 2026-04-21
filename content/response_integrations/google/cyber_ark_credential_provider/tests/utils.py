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

from pathlib import Path
from cyber_ark_credential_provider.core.datamodels import (
    IntegrationParameters
)

from integration_testing.common import get_def_file_content


def read_config() -> IntegrationParameters:
    """Read config.json to get the integration credentials.

    Returns:
        IntegrationParameters: Integration parameters
    """
    config = get_def_file_content("config.json")
    sdk_path_str = config.get("Path to clipasswordsdk")
    username = config.get("Username for Credential Provider for Linux")
    docker_gateway_ip = config.get("Docker Gateway IP Address")
    rsa_public_key_data = config.get("RSA Public Key")
    ssh_private_key_path_str = config.get("SSH Private Key Path")
    password = config.get("Password for Credential Provider for Linux")

    return IntegrationParameters(
        sdk_path=Path(sdk_path_str),
        username=username,
        docker_gateway_ip=docker_gateway_ip,
        rsa_public_key_data=rsa_public_key_data,
        ssh_private_key_path=(
            Path(ssh_private_key_path_str) if ssh_private_key_path_str else None
        ),
        password=password,
    )

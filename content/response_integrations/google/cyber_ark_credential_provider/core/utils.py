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

import ipaddress
from pathlib import Path

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import ChronicleSOAR
from . import constants
from .datamodels import IntegrationParameters
from . import exceptions


def get_integration_parameters(soar_action: ChronicleSOAR) -> IntegrationParameters:
    """Extracts CyberArk Credential Provider integration configuration parameters.

    Args:
        soar_action: The ChronicleSOAR action object.

    Returns:
        IntegrationParameters: An IntegrationParameters object containing the
        extracted configuration parameters.
    """
    sdk_path_str: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Path to clipasswordsdk",
        is_mandatory=True,
        print_value=True,
    )
    username: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Username for Credential Provider for Linux",
        is_mandatory=True,
        print_value=True,
    )
    docker_gateway_ip: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Docker Gateway IP Address",
        is_mandatory=True,
        print_value=True,
    )
    rsa_public_key_data: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="RSA Public Key",
        is_mandatory=True,
    )
    ssh_private_key_path_str: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="SSH Private Key Path",
    )
    password: str = extract_configuration_param(
        soar_action,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Password for Credential Provider for Linux",
    )

    ssh_private_key_path = (
        Path(ssh_private_key_path_str) if ssh_private_key_path_str else None
    )
    integration_parameters: IntegrationParameters = IntegrationParameters(
        sdk_path=Path(sdk_path_str),
        username=username,
        docker_gateway_ip=docker_gateway_ip,
        rsa_public_key_data=rsa_public_key_data,
        ssh_private_key_path=ssh_private_key_path,
        password=password,
    )

    return integration_parameters


def validate_ip_address(ip: str) -> None:
    """Validates whether an IP address is valid.

    Args:
        ip(str): The IP address to validate.

    Raises:
        CyberArkCredentialProviderValidationError: If the IP address is invalid.
    """
    try:
        ipaddress.ip_address(ip)

    except ValueError as e:
        raise exceptions.CyberArkCredentialProviderValidationError(
            f"Invalid Docker Gateway IP: {ip}. Please provide a valid IP address."
        ) from e

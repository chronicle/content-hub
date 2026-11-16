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
from typing import TYPE_CHECKING, Any

from TIPCommon.extraction import extract_script_param
from TIPCommon.types import SingleJson
from . import constants
from . import exceptions
from .datamodels import ConfigurationParameters


if TYPE_CHECKING:
    from TIPCommon.data_models import (
        ConnectorCard,
        InstalledIntegrationInstance,
    )


def build_instance_name_lookup(
    instances: list[InstalledIntegrationInstance],
) -> constants.NameIdentifierMap:
    """Build a name-to-identifier mapping for instances."""
    return {inst.instance_name: inst.identifier for inst in instances}


def build_connector_name_lookup(
    connector_cards: list[ConnectorCard],
) -> constants.NameIdentifierMap:
    """Build and return a display_name-to-identifier mapping for connectors."""
    return {card.display_name: card.identifier for card in connector_cards}


def build_job_name_lookup(job_instances: list[SingleJson]) -> dict[str, SingleJson]:
    """Build a display-name -> job-dict lookup. 1P uses ``displayName``; Legacy uses ``name``."""
    return {
        inst.get("displayName") or inst.get("name", ""): inst for inst in job_instances
    }


def build_param_index(parameters: list[SingleJson]) -> dict[str, int]:
    """Build a parameter name -> list-index lookup. 1P params use ``displayName``; Legacy uses ``name``."""
    param_index: dict[str, int] = {}
    for idx, param in enumerate(parameters):
        param_name: str = param.get("displayName") or param.get("name", "")
        param_index[param_name] = idx

    return param_index


def get_configuration_parameters(soar_sdk_object: Any) -> ConfigurationParameters:
    """Extracts CyberArk Credential Provider configuration parameters from Integration Instance configuration.

    Args:
        soar_sdk_object (Any): The ChronicleSOAR Action or SDK execution object.

    Returns:
        ConfigurationParameters: A ConfigurationParameters object containing the
        extracted configuration parameters.
    """
    logger = getattr(soar_sdk_object, "LOGGER", None) or getattr(
        soar_sdk_object, "logger", None
    )
    if logger:
        logger.info(
            "Extracting CyberArk configuration parameters from Integration Instance configuration."
        )

    config = soar_sdk_object.get_configuration(constants.INTEGRATION_NAME)

    sdk_path_str = extract_script_param(
        soar_sdk_object,
        input_dictionary=config,
        param_name=constants.PATH_TO_CLIPASSWORDSDK_CONFIG_PARAM,
        is_mandatory=True,
        print_value=True,
    )
    username = extract_script_param(
        soar_sdk_object,
        input_dictionary=config,
        param_name=constants.USERNAME_CONFIG_PARAM,
        is_mandatory=True,
        print_value=True,
    )
    docker_gateway_ip = extract_script_param(
        soar_sdk_object,
        input_dictionary=config,
        param_name=constants.DOCKER_GATEWAY_IP_CONFIG_PARAM,
        is_mandatory=True,
        print_value=True,
    )
    host_public_key_data = extract_script_param(
        soar_sdk_object,
        input_dictionary=config,
        param_name=constants.HOST_PUBLIC_KEY_CONFIG_PARAM,
        is_mandatory=True,
    )
    ssh_private_key_path_str = extract_script_param(
        soar_sdk_object,
        input_dictionary=config,
        param_name=constants.SSH_PRIVATE_KEY_PATH_CONFIG_PARAM,
        is_mandatory=False,
    )
    password = extract_script_param(
        soar_sdk_object,
        input_dictionary=config,
        param_name=constants.PASSWORD_CONFIG_PARAM,
        is_mandatory=False,
    )

    ssh_private_key_path = (
        Path(ssh_private_key_path_str) if ssh_private_key_path_str else None
    )

    return ConfigurationParameters(
        sdk_path=Path(sdk_path_str),
        username=username,
        docker_gateway_ip=docker_gateway_ip,
        host_public_key_data=host_public_key_data,
        ssh_private_key_path=ssh_private_key_path,
        password=password,
    )


def validate_ip_address(ip_address: str) -> None:
    """Validates whether an IP address is valid.

    Args:
        ip_address (str): The IP address to validate.

    Raises:
        CyberArkCredentialProviderValidationError: If the IP address is invalid.
    """
    try:
        ipaddress.ip_address(ip_address)

    except ValueError as e:
        raise exceptions.CyberArkCredentialProviderValidationError(
            f"Invalid Docker Gateway IP: {ip_address}. Please provide a valid IP address."
        ) from e

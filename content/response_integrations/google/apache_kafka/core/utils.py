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

import base64
import binascii
from functools import partial
import re
from typing import TYPE_CHECKING

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.exceptions import ConnectorSetupError
from TIPCommon.transformation import dict_to_flat

from ..core.config_models import KafkaConfigurationParameters

if TYPE_CHECKING:
    from typing import Any, Callable

    from TIPCommon.types import ChronicleSOAR, SingleJson


def validate_base64_string(param_name: str, param_value: str) -> None:
    """
    Validates if a given string is a valid base64-encoded string.

    Args:
        param_name (str): The name of the parameter being validated.
        param_value (str): The string value to validate.

    Raises:
        ConnectorSetupError: If the string is not a valid base64 string.
    """
    if not param_value:
        return

    try:
        base64.b64decode(param_value, validate=True)

    except (binascii.Error, ValueError) as e:
        raise ConnectorSetupError(
            f"Invalid base64 content for parameter '{param_name}'. Error: {e}"
        ) from e


def get_integration_parameters(
    soar_action: ChronicleSOAR,
) -> KafkaConfigurationParameters:
    """Retrieve integration parameters from the SiemplifyAction object.

    Args:
        soar_action (ChronicleSOAR): The SOAR action or connector object.

    Returns:
        KafkaConfigurationParameters: Kafka configuration parameters object.
    """
    bootstrap_servers: str = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="Kafka Brokers",
        is_mandatory=True,
        print_value=True,
    )
    use_ssl: bool = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="Use TLS for connection",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    use_sasl_ssl: bool = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="Use SASL PLAIN with TLS for connection",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    sasl_username: str = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="SASL PLAIN Username",
        print_value=True,
    )
    sasl_password: str = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="SASL PLAIN Password",
        remove_whitespaces=False,
    )
    ca_certificate: str = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="CA certificate of Kafka server",
        remove_whitespaces=False,
    )
    client_certificate: str = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="Client certificate",
        remove_whitespaces=False,
    )
    client_certificate_key: str = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="Client certificate key",
        remove_whitespaces=False,
    )
    client_certificate_key_password: str = extract_configuration_param(
        siemplify=soar_action,
        provider_name="ApacheKafka",
        param_name="Client certificate key password",
        remove_whitespaces=False,
    )

    validate_base64_string("CA certificate of Kafka server", ca_certificate)
    validate_base64_string("Client certificate", client_certificate)
    validate_base64_string("Client certificate key", client_certificate_key)

    return KafkaConfigurationParameters(
        bootstrap_servers=bootstrap_servers,
        use_ssl=use_ssl,
        use_sasl_ssl=use_sasl_ssl,
        sasl_username=sasl_username,
        sasl_password=sasl_password,
        ca_certificate=ca_certificate,
        client_certificate=client_certificate,
        client_certificate_key=client_certificate_key,
        client_certificate_key_password=client_certificate_key_password,
    )


def get_default_severity(value: str) -> int:
    """Parse a string value to a default severity integer.

    Args:
        value (str): The string value to parse.

    Returns:
        int: The rounded integer severity.

    Raises:
        ValueError: If the value cannot be converted to a number.
    """
    try:
        return round(float(value))

    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid severity default value - {value}, please supply a valid integer."
        ) from e


def get_int_float_severity(value: str) -> int | None:
    """Parse a string value to an integer or float severity.

    Args:
        value (str): The string value to parse.

    Returns:
        int | None: The rounded integer severity, or None if input is None.

    Raises:
        ValueError: If the value cannot be converted to a number.
    """
    try:
        return value if value is None else round(float(value))

    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid severity value - {value}, please supply a "
            "transformation or switch to an integer or float field."
        ) from e


def get_mapped_severity(value: str, transformation: SingleJson) -> int | None:
    """Map a value to a severity using a transformation dictionary.

    Args:
        value (str): The value to map.
        transformation (SingleJson): The dictionary mapping values to severities.

    Returns:
        int | None: The mapped severity, or None if not found.

    Raises:
        ValueError: If the mapped value cannot be converted to a number.
    """
    try:
        value_: str | None = transformation.get(value)
        return value_ if value_ is None else round(float(value_))

    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid severity value - {value}, provided transformation is not "
            f"valid, please recheck it or switch to an integer or float field."
        ) from e

    except AttributeError as e:
        raise ValueError(
            "Invalid value for Severity Mapping JSON has been provided. "
            "Please use an empty string for integer and float fields."
        ) from e


def build_severity_transformation(
    transformation: str,
) -> Callable[[str], int | None]:
    """Build severity key: transformation function mapping."""
    if transformation:
        return partial(get_mapped_severity, transformation=transformation)

    return get_int_float_severity


def get_field_from_payload(json_payload: SingleJson | None, field_name: str) -> Any:
    """Gets a potentially nested value from a JSON payload.

    Args:
        json_payload (SingleJson | None): The JSON payload to search in.
        field_name (str): The dot-notation field name to retrieve.

    Returns:
        Any: The value of the field, or None if not found.
    """
    if not field_name or not isinstance(json_payload, dict):
        return None

    flat_payload: SingleJson = dict_to_flat(json_payload)
    lookup_key: str = field_name.replace(".", "_")

    return flat_payload.get(lookup_key)


def format_template(
    template: str | None,
    event: SingleJson,
) -> str:
    """Formats a template string by replacing placeholders with values from the event.

    Args:
        template: Template string with placeholders in square brackets [key].
                 If None or empty, returns empty string.
        event: Dictionary containing values to substitute in the template.

    Returns:
        str: Formatted string with all placeholders replaced with their values.
        If a key is not found in the event, it's replaced with an empty string.
    """
    if not template:
        return ""

    flat_event: SingleJson = dict_to_flat(event)

    def replace_key(match: re.Match) -> str:
        key: str = match.group(1).replace(".", "_")
        value: Any = flat_event.get(key)
        if value is None:
            return ""

        return str(value)

    return re.sub(r"\[([^\]]+)\]", replace_key, template)

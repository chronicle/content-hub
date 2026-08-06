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

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, cast

from TIPCommon.extraction import extract_configuration_param, extract_connector_param
from TIPCommon.validation import ParameterValidator

from .consts import INTEGRATION_NAME, VALID_STATUS_CODES
from .exceptions import AWSGuardDutyStatusCodeError, AWSGuardDutyValidationError

if TYPE_CHECKING:
    from SiemplifyAction import SiemplifyAction
    from SiemplifyConnectorExecution import SiemplifyConnectorExecution


@dataclass
class AWSGuardDutyConfig:
    """AWS GuardDuty integration configuration.

    Attributes:
        aws_access_key: The AWS Access Key ID.
        aws_secret_key: The AWS Secret Access Key.
        aws_default_region: The default region name.
        role_arn: The AWS role to assume.
        service_account_json: Google service account credentials.
        workload_identity_email: Workload identity email.

    """

    aws_access_key: str | None
    aws_secret_key: str | None
    aws_default_region: str
    role_arn: str | None
    service_account_json: dict[str, Any] | None
    workload_identity_email: str | None


def remove_empty_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Remove keys from dictionary that has the value None.

    Args:
        kwargs: Key value arguments.

    Returns:
        Dictionary without keys that have the value None.

    """
    return {k: v for k, v in kwargs.items() if v is not None}


def validate_filter_json_object(filter_json: str) -> dict[str, Any]:
    """Load filter JSON object string to a dictionary.

    Args:
        filter_json: Filter JSON object string.

    Returns:
        The deserialized filter JSON object.

    Raises:
        AWSGuardDutyValidationError: If failed to load filter JSON object string.

    """
    try:  # validate filter json object
        return json.loads(filter_json)
    except (json.JSONDecodeError, TypeError) as err:
        msg = "Failed to validate Filter JSON Object."
        raise AWSGuardDutyValidationError(msg) from err


T = TypeVar("T")


def get_mapped_value(mappings: dict[str, T], key: str | None, default_value: str | None) -> T | None:
    """Get mapped value of 'key' parameter.

    If default value is provided, and key equals default_value, None
    will be returned. Otherwise, if key does not exist in mappings,
    an AWSGuardDutyValidationError will be raised.

    Args:
        mappings: Dict of mapped keys to values.
        key: Key to check if there is mapped value in mappings.
        default_value: Used to prevent exception raising if key not in mappings.

    Returns:
        Value of key in mappings if key exists in mappings dictionary,
        None if key is default_value or key is None.

    Raises:
        AWSGuardDutyValidationError: If key is not in mappings and is not
            the default value.

    """
    if not key or key == default_value:
        return None
    if key not in mappings:
        msg = f"Failed to validate parameter {key}"
        raise AWSGuardDutyValidationError(msg)
    return mappings.get(key)


def load_csv_to_list(csv: str, param_name: str) -> list[str]:
    """Load comma separated values represented as string to a list.

    Args:
        csv: Comma separated values with delimiter ','.
        param_name: The name of the variable we are validating.

    Returns:
        List of values.

    Raises:
        AWSGuardDutyValidationError: If failed to parse csv.

    """
    try:
        return [t.strip() for t in csv.split(",")]
    except AttributeError as err:
        msg = f"Failed to parse parameter {param_name}"
        raise AWSGuardDutyValidationError(msg) from err


def load_kv_csv_to_dict(kv_csv: str, param_name: str) -> dict[str, str]:
    """Load comma separated values of 'key':'value' represented as string to dictionary.

    Args:
        kv_csv: Comma separated values of 'key':'value' represented as a string.
        param_name: Name of the parameter.

    Returns:
        Dict of key:value.

    Raises:
        AWSGuardDutyValidationError: If failed to parse kv_csv.

    """
    try:
        return {kv.split(":")[0].strip(): kv.split(":")[1].strip() for kv in kv_csv.split(",")}
    except (AttributeError, IndexError) as err:
        msg = f"Failed to parse parameter {param_name}"
        raise AWSGuardDutyValidationError(msg) from err


def extract_action_params(siemplify: SiemplifyAction) -> AWSGuardDutyConfig:
    """Extract AWS GuardDuty integration configuration parameters for actions.

    Args:
        siemplify: The Siemplify action object.

    Returns:
        The extracted and validated integration parameters.

    Raises:
        ValueError: If AWS Access Key ID and AWS Secret Key are required when
            Role ARN is not provided.

    """
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    role_arn = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Role ARN",
    )

    service_account_json_str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Service Account JSON",
    )

    validator = ParameterValidator(siemplify)
    service_account_json = (
        validator.validate_json(
            param_name="Service Account JSON",
            json_string=service_account_json_str,
            print_value=False,
        )
        if service_account_json_str
        else None
    )

    workload_identity_email = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Workload Identity Email",
    )

    if not role_arn and (not aws_access_key or not aws_secret_key):
        msg = "AWS Access Key ID and AWS Secret Key are required when Role ARN is not provided."
        raise ValueError(msg)

    if not aws_default_region:
        msg = "AWS Default Region is required."
        raise ValueError(msg)

    return AWSGuardDutyConfig(
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        aws_default_region=aws_default_region,
        role_arn=role_arn,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )


def extract_connector_params(siemplify: SiemplifyConnectorExecution) -> AWSGuardDutyConfig:
    """Extract AWS GuardDuty integration configuration parameters for connectors.

    Args:
        siemplify: The Siemplify connector object.

    Returns:
        The extracted and validated integration parameters.

    Raises:
        ValueError: If AWS Access Key ID and AWS Secret Key are required when
            Role ARN is not provided.

    """
    aws_access_key = extract_connector_param(
        siemplify,
        param_name="AWS Access Key ID",
    )

    aws_secret_key = extract_connector_param(
        siemplify,
        param_name="AWS Secret Key",
    )

    aws_default_region = extract_connector_param(
        siemplify,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    role_arn = extract_connector_param(
        siemplify,
        param_name="Role ARN",
    )

    service_account_json_str = extract_connector_param(
        siemplify,
        param_name="Service Account JSON",
    )

    validator = ParameterValidator(siemplify)
    service_account_json = (
        validator.validate_json(
            param_name="Service Account JSON",
            json_string=service_account_json_str,
            print_value=False,
        )
        if service_account_json_str
        else None
    )

    workload_identity_email = extract_connector_param(
        siemplify,
        param_name="Workload Identity Email",
    )

    if not role_arn and (not aws_access_key or not aws_secret_key):
        msg = "AWS Access Key ID and AWS Secret Key are required when Role ARN is not provided."
        raise ValueError(msg)

    if not aws_default_region:
        msg = "AWS Default Region is required."
        raise ValueError(msg)

    return AWSGuardDutyConfig(
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        aws_default_region=aws_default_region,
        role_arn=role_arn,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )


def extract_integration_params(
    siemplify: SiemplifyAction | SiemplifyConnectorExecution,
    *,
    is_connector: bool = False,
) -> AWSGuardDutyConfig:
    """Extract AWS GuardDuty integration configuration parameters.

    Args:
        siemplify: The Siemplify action or connector object.
        is_connector: True if called from a connector.

    Returns:
        The extracted and validated integration parameters.

    """
    if is_connector:
        return extract_connector_params(cast("SiemplifyConnectorExecution", siemplify))
    return extract_action_params(cast("SiemplifyAction", siemplify))


def validate_response(response: dict[str, Any], error_msg: str = "An error occurred") -> None:
    """Validate client Security Hub response status code.

    Args:
        response: client Security Hub response.
        error_msg: Error message to display in case of an error.

    Raises:
        AWSGuardDutyStatusCodeError: If status code is not 200.

    """
    if response.get("ResponseMetadata", {}).get("HTTPStatusCode") not in VALID_STATUS_CODES:
        msg = f"{error_msg}. Response code: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}"
        raise AWSGuardDutyStatusCodeError(msg)

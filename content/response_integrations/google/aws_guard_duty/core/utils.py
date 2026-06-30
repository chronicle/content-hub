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
from typing import Any, TYPE_CHECKING

from TIPCommon.extraction import extract_configuration_param
from TIPCommon.validation import ParameterValidator

from .consts import INTEGRATION_NAME
from .exceptions import AWSGuardDutyValidationException

if TYPE_CHECKING:
    from SiemplifyAction import SiemplifyAction


def remove_empty_kwargs(kwargs):
    """
    Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def validate_filter_json_object(filter_json):
    """
    Loads filter json object string to a dictionary.
    :param filter_json: {str} of filter json object
    :return: {dict} of filter_json
            raise AWSGuardDutyValidationException if failed to load filter json object string
                  to a dictionary
    """
    try:  # validate filter json object
        filter_json = json.loads(filter_json)
    except Exception:
        raise AWSGuardDutyValidationException("Failed to validate Filter JSON Object.")

    return filter_json


def get_mapped_value(mappings, key, default_value):
    """
    Returns mapped value of 'key' parameter. if default value is provided, and key equals default_value, None will be returned.
    otherwise, if key does not exist in mappings - an AWSGuardDutyValidationException will be thrown.

    :param mappings: {dict} of mapped keys to values
    :param key: {str} key to check if there is mapped value in mappings. if key is None, None will be returned.
    :param default_value: {str} used to prevent Exception throwing if key not in mappings
    :return: {str} value of key in mappings if key exists in mappings dictionary.
             None - if key=default_value or key is None
             otherwise if key exists in mappings the value will be returned {str}
             otherwise raise AWSGuardDutyValidationException
    """
    if not key or key == default_value:
        return None
    if key not in mappings:
        raise AWSGuardDutyValidationException(f"Failed to validate parameter {key}")
    return mappings.get(key)


def load_csv_to_list(csv, param_name):
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AWSGuardDutyValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise AWSGuardDutyValidationException(f"Failed to parse parameter {param_name}")


def load_kv_csv_to_dict(kv_csv, param_name):
    """
    Load comma separated values of 'key':'value' represented as string to dictionary
    :param kv_csv: {str} of comma separated values of 'key':'value' represented as a string
    :param param_name: {str} name of the parameter
    :return: {dict} of key:value
            raise AWSGuardDutyValidationException if failed to parse kv_csv
    """
    try:
        return {
            kv.split(":")[0].strip(): kv.split(":")[1].strip()
            for kv in kv_csv.split(",")
        }
    except Exception:
        raise AWSGuardDutyValidationException(f"Failed to parse parameter {param_name}")


def extract_integration_params(
    siemplify: SiemplifyAction,
) -> tuple[
    str | None,
    str | None,
    str,
    str | None,
    dict[str, Any] | None,
    str | None,
]:
    """Extracts AWS GuardDuty integration configuration parameters.

    Args:
        siemplify: The Siemplify action object.

    Returns:
        The extracted and validated integration parameters.
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
        raise ValueError(
            "AWS Access Key ID and AWS Secret Key are required when Role ARN is not provided."
        )


    return (
        aws_access_key,
        aws_secret_key,
        aws_default_region,
        role_arn,
        service_account_json,
        workload_identity_email,
    )

from __future__ import annotations
import collections

import json
import urllib.parse

from bs4 import BeautifulSoup
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.gcp import validate_impersonation
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from google_cloud_armor.core import constants
from google_cloud_armor.core import exceptions
from google_cloud_armor.core import AuthenticationManager as auth_manager
from google_cloud_armor.core import GoogleCloudArmorManager as api_manager


IntegrationParams = collections.namedtuple(
    "IntegrationParams", ["auth_params", "api_params"]
)


def get_integration_params(soar_action: SiemplifyAction) -> IntegrationParams:
    """Get Google Cloud Armor IntegrationParams object for session auth params and
    api params.

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object.

    Returns:
        IntegrationParams: Named tuple IntegrationParams.
    """
    api_root = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    project_id = extract_configuration_param(
        soar_action,
        param_name="Project ID",
        provider_name=constants.PROVIDER_NAME,
        print_value=True,
    )
    workload_identity_email = extract_configuration_param(
        soar_action,
        param_name="Workload Identity Email",
        provider_name=constants.PROVIDER_NAME,
        print_value=True,
    )
    user_service_account = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="User Service Account",
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        soar_action,
        provider_name=constants.PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    auth_params = auth_manager.SessionAuthenticationParameters(
        api_root=api_root,
        project_id=project_id,
        workload_identity_email=workload_identity_email,
        user_service_account=user_service_account,
        verify_ssl=verify_ssl,
    )
    api_params = api_manager.ApiParameters(api_root=api_root, project_id=project_id)
    integration_params = IntegrationParams(
        auth_params=auth_params, api_params=api_params
    )

    return integration_params


def validate_configuration_params(
    soar_action: SiemplifyAction,
    auth_params: auth_manager.SessionAuthenticationParameters,
    api_params: api_manager.ApiParameters,
) -> None:
    """Validate configuration parameters for auth params and api params wi and user
        service account attributes.

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object.
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object.
        api_params (api_manager.ApiParameters): api params object.
    """
    validator = ParameterValidator(soar_action)
    if not is_empty_string_or_none(auth_params.user_service_account):
        user_service_account = validator.validate_json(
            param_name="User Service Account",
            json_string=auth_params.user_service_account,
            print_value=False,
        )
        api_params.user_service_account = auth_params.user_service_account = (
            user_service_account
        )

    if not is_empty_string_or_none(auth_params.workload_identity_email):
        workload_identity_email = validator.validate_email(
            param_name="Workload Identity Email",
            email=auth_params.workload_identity_email,
            print_value=True,
        )
        api_params.workload_identity_email = auth_params.workload_identity_email = (
            workload_identity_email
        )


def get_full_url(
    api_root: str, endpoint_id: str, endpoints: dict[str, str], **kwargs
) -> str:
    """Construct the full URL using a URL identifier and optional variables.

    Args:
        api_root (str): The root of the API endpoint.
        url_id (str): The identifier for the specific URL.
        endpoints (dict[str, str]): endpoints dictionary object.
        kwargs (dict): Variables passed for string formatting.

    Returns:
        str: The full URL constructed by combining the API root, URL identifier, and
            variables.
    """
    return urllib.parse.urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response_info: dict,
    content: dict | str,
    sensitive_data_arr: list | None = None,
    error_msg: str = "An error occurred",
) -> None:
    """
    Validate response
    Args:
        response_info (dict): The response info
        content (dict): The response content
        sensitive_data_arr (list | None): The list of sensitive data
        error_msg (str): Default message to display on error

    Raises:
        GoogleCloudArmorError: If there is any error in the response.
        GoogleCloudArmorStatusNotFoundError: If the requested resource is not found.
        GoogleCloudArmorPermissionsDeniedError: If permission is denied to access the
            resource.
        GoogleCloudArmorInvalidRegionError: If an invalid region is provided.
    """
    status_code = int(response_info.get("status", ""))
    if 200 <= status_code < 400:
        return

    try:
        content = json.loads(content)
    except json.decoder.JSONDecodeError:
        pass

    validate_impersonation(content)

    message = get_error_message_from_response(status_code, content, error_msg)

    if sensitive_data_arr:
        message = encode_sensitive_data(message, sensitive_data_arr)

    if status_code == constants.NOT_FOUND_STATUS:
        raise exceptions.GoogleCloudArmorStatusNotFoundError(f"{message}")

    if status_code == constants.PERMISSION_DENIED_STATUS:
        raise exceptions.GoogleCloudArmorPermissionsDeniedError(f"{message}")

    if status_code == constants.BAD_REQUEST and constants.REGION_ERROR in message:
        raise exceptions.GoogleCloudArmorInvalidRegionError(f"{message}")

    raise exceptions.GoogleCloudArmorError(f"{message}")


def get_error_message_from_response(
    status_code: int, content: bytes | dict, error_msg: str = "An error occurred"
) -> str:
    """Gets the error message from the response content

    Args:
        status_code (int): API HTTP status code.
        content (bytes | dict): Response content
        error_msg (str): Generic error message to be applied at the beginning
            of each error message

    Returns:
        str: An error message
    """
    if isinstance(content, dict):
        message = content.get("error", {}).get("message")
        error_text = message
    else:
        error_text = BeautifulSoup(content, "html.parser").p.text

    return f"{error_msg}: {error_text}\nResponse Status Code: {status_code}"


def encode_sensitive_data(message: str, sensitive_data_arr: list) -> str:
    """
    Encode sensitive data
    Args:
        message (str): The error message which may contain sensitive data
        sensitive_data_arr (list): The list of sensitive data
    Returns:
        str: The error message with encoded sensitive data
    """
    for sensitive_data in sensitive_data_arr:
        message = message.replace(sensitive_data, encode_data(sensitive_data))

    return message


def encode_data(sensitive_data: str) -> str:
    """
    Encode string
    Args:
        sensitive_data: (str): String to be encoded
    Returns:
        (str): Encoded string
    """
    if len(sensitive_data) > 1:
        return f"{sensitive_data[0]}...{sensitive_data[-1]}"

    return sensitive_data


def get_environment_string(region: str) -> str:
    return region if region == constants.DEFAULT_ENVIRONMENT else f"regions/{region}"

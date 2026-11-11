from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from TIPCommon.exceptions import BadGatewayError, DeadlineExceededError

from scc_enterprise.core.GoogleSecurityCommandCenterExceptions import (
    GoogleSecurityCommandCenterException,
    GoogleSecurityCommandCenterInvalidJsonException,
    GoogleSecurityCommandCenterInvalidProject,
    GoogleSecurityCommandCenterNotFound,
)
from scc_enterprise.core.GoogleSecurityCommandCenterConstants import (
    SUCCESS_STATUSES,
    CAI_AWS_RESOURCE_TEMPLATE,
    CAI_AZURE_RESOURCE_TEMPLATE,
)
from scc_enterprise.core.SCCEnterpriseDatamodels import CloudProviderEnum


def validate_response(response, sensitive_data_arr=None, error_msg="An error occurred"):
    """
    Validate response
    :param response: {dict} The response info
    :param sensitive_data_arr: {list} The list of sensitive data
    :param error_msg: {str} Default message to display on error
    """
    try:
        if response.status_code not in SUCCESS_STATUSES:
            raise Exception

    except Exception:
        content = response.content
        try:
            content = json.loads(response.content)
        except Exception:
            pass

        if isinstance(content, dict) and content.get("error", {}).get("message"):
            error_text = content.get("error", {}).get("message")
        else:
            if not BeautifulSoup(content, "html.parser").p:
                error_text = "Unknown error."
            else:
                error_text = BeautifulSoup(content, "html.parser").p.text

        if response.status_code == 502 or "502. That’s an error." in error_text:
            raise BadGatewayError(f"{error_msg}: {error_text}")

        elif "Deadline expired before operation could complete." in error_text:
            raise DeadlineExceededError(f"{error_msg}: {error_text}")

        elif response.status_code == 404:
            raise GoogleSecurityCommandCenterNotFound(f"{error_msg}: {error_text}")

        if sensitive_data_arr:
            raise GoogleSecurityCommandCenterException(
                encode_sensitive_data(
                    str(f"{error_msg}: {error_text}"), sensitive_data_arr
                )
            )

        raise GoogleSecurityCommandCenterException(f"{error_msg}: {error_text}")

    return True


# move to TIPCommon
def encode_sensitive_data(message, sensitive_data_arr):
    """
    Encode sensitive data
    :param message: {str} The error message which may contain sensitive data
    :param sensitive_data_arr: {list} The list of sensitive data
    :return: {str} The error message with encoded sensitive data
    """
    for sensitive_data in sensitive_data_arr:
        message = message.replace(sensitive_data, encode_data(sensitive_data))

    return message


# move to TIPCommon
def encode_data(sensitive_data):
    """
    Encode string
    :param sensitive_data: {str} String to be encoded
    :return: {str} Encoded string
    """
    if len(sensitive_data) > 1:
        return f"{sensitive_data[0]}...{sensitive_data[-1]}"

    return sensitive_data


# move to TIPCommon
def parse_string_to_dict(string):
    """
    Parse json string to dict
    :param string: string to parse
    :return: {dict} parsed dict
    """
    try:
        return json.loads(string)
    except Exception:
        raise GoogleSecurityCommandCenterInvalidJsonException


def validate_request_id(id):
    """
    Helper function for validating ID
    :param id: id which function will check
    """
    if not id:
        raise GoogleSecurityCommandCenterInvalidProject


def get_asset_resource_name(resource_data: dict) -> str:
    """returns a Finding resource name in human readable format

    Args:
        resource_data (dict):
            resource data of the finding data, found under "resource"

    Returns:
        str: Finding resource name in human readable format

    Raises:
        GoogleSecurityCommandCenterException: If failed to build resource name
    """
    try:
        resource_name = resource_data["name"]
        if "compute" in resource_data["type"]:
            if "projects/" in resource_name:
                project_display_name = resource_data.get("gcpMetadata", {}).get(
                    "projectDisplayName"
                ) or resource_data.get("projectDisplayName")
                resource_name = re.sub(
                    pattern=r"/projects/[0-9]+/",
                    repl=f"/projects/{project_display_name}/",
                    string=resource_name,
                )

            resource_name = re.sub(
                pattern=r"/[0-9]+$",
                repl=f'/{resource_data["displayName"]}',
                string=resource_name,
            )
        return resource_name
    except Exception as e:
        raise GoogleSecurityCommandCenterException(
            f"Could not build readable resource name from resource data: {e}"
        ) from e


def get_non_gcp_resource_name(
    resource_data: dict, cloud_provider: CloudProviderEnum, organization_id: str
) -> str:
    """Builds a resource name in CAI format for cloud connections resource.

    Args:
        resource_data: Resource data object from Pub/Sub finding
        cloud_provider: Cloud provider of a resource
        organization_id: Finding Org ID

    Returns:
        CAI compatible resource name

    Raises:
        GoogleSecurityCommandCenterException: If failed to build resource name
    """
    try:
        if cloud_provider == CloudProviderEnum.AWS:
            return CAI_AWS_RESOURCE_TEMPLATE.format(
                organization_id=organization_id, resource_arn=resource_data["name"]
            )

        if cloud_provider == CloudProviderEnum.AZURE:
            return CAI_AZURE_RESOURCE_TEMPLATE.format(
                organization_id=organization_id, resource_arn=resource_data["name"]
            )

        raise GoogleSecurityCommandCenterException(
            f"Unsupported cloud provider: {cloud_provider}"
        )
    except Exception as e:
        raise GoogleSecurityCommandCenterException(
            f"Could not build readable resource name from resource data: {e}"
        ) from e

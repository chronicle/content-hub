from __future__ import annotations
import hashid
import requests
from .constants import MD5, SHA1, SHA256, TIMEOUT_THRESHOLD
from .VMRayExceptions import VMRayApiException, NotFoundException
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import unix_now


def validate_response(response):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :return: {void}
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        if response.status_code == 404:
            raise NotFoundException(f"Error:{error}, response:{error.response.content}")

        raise VMRayApiException(f"Error:{error}, response:{error.response.content}")


def get_type_of_hash(hash_id):
    """
    Get type of hash
    :param hash_id: {str} hash id
    :return: {str} type of hash
    """
    hash_object = hashid.HashID()
    prop = hash_object.identifyHash(hash_id)

    for i in prop:
        type_of_hash = i[0]
        if "SHA-1" in type_of_hash:
            return SHA1
        elif "MD" in type_of_hash:
            return MD5
        elif "256" in type_of_hash:
            return SHA256


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def convert_list_to_comma_string(values_list):
    """
    Convert list to comma-separated string
    :param values_list: List of values
    :return: String with comma-separated values
    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def is_approaching_timeout(action_starting_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param action_starting_time: {int} Action start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - action_starting_time
    return (
        processing_time_ms
        > (python_process_timeout - action_starting_time) * TIMEOUT_THRESHOLD
    )


def get_system_versions(siemplify):
    """
    Get siemplify platform and integration versions
    :param siemplify: {siemplify} Siemplify object
    :return: {dict} dict containing platform version and integration version
    """
    return {
        "platform_version": siemplify.get_system_version(),
        "integration_version": siemplify.get_integration_version(
            siemplify.integration_identifier
        ),
    }


# TODO: Remove when TIPCommon is updated to version 2.0.2 and use TIPCommon.utils
#       instead
def get_entity_original_identifier(entity: EntityTypes) -> str:
    """Helper function for getting entity original identifier

    Args:
        entity (EntityTypes): entity from which function will get original
            identifier

    Returns:
        str: Entity original identifier.
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)

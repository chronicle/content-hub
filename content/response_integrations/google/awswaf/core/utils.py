from __future__ import annotations
import ipaddress
import json
from . import consts
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime
from .exceptions import AWSWAFValidationException


def load_csv_to_list(csv, param_name) -> list:
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma seperated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AWSWAFValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise AWSWAFValidationException(f"Failed to parse parameter {param_name}")


def load_csv_to_set(csv, param_name) -> set:
    """
    Load comma separated values represented as string to a set
    :param csv: {str} of comma seperated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {set} of values
            raise AWSWAFValidationException if failed to parse csv
    """
    try:
        return {t.strip() for t in csv.split(",")}
    except Exception:
        raise AWSWAFValidationException(f"Failed to parse parameter {param_name}")


def validate_json_object(json_object, json_object_name) -> dict:
    """
    Loads filter json object string to a dictionary.
    :param json_object: {str} of filter json object
    :return: {dict} of json_object
            raise AWSWAFValidationException if failed to load filter json object string
                  to a dictionary
    """
    try:  # validate json object
        loaded_json = json.loads(json_object)
    except Exception:
        raise AWSWAFValidationException(f"Failed to validate {json_object_name}")

    return loaded_json


def remove_empty_kwargs(**kwargs) -> dict:
    """
    Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: {dict} dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def get_mapped_value(mappings, key):
    """
    Returns mapped value of 'key' parameter. if default value is provided, and key equals default_value, None will be returned.
    otherwise, if key does not exist in mappings - an AWSSecurityHubValidationException will be thrown.

    :param mappings: {dict} of mapped keys to values
    :param key: {str} key to check if there is mapped value in mappings. if key is None, None will be returned.
    :param default_value: {str} used to prevent Exception throwing if key not in mappings
    :return: {str} value of key in mappings if key exists in mappings dictionary.
             None - if key=default_value or key is None
             otherwise if key exists in mappings the value will be returned {str}
             otherwise raise AWSWAFValidationException
    """
    if key not in mappings:
        raise AWSWAFValidationException(f"Failed to validate parameter {key}")
    return mappings.get(key)


def get_ip_address_version(address) -> int:
    """
    Return ip version IP version
    :param address:  {str} ip address of version 4 or 6
    :return: {int} of IP Version. If IP address is invalid or ip version is not recognized -1 will be returned
    """
    address = address.strip()
    try:
        return ipaddress.ip_address(
            address
        ).version  # if not masked and valid return version
    except Exception:
        pass
    try:
        return ipaddress.ip_network(
            address
        ).version  # if masked and valid return version
    except Exception:
        pass
    return -1


def get_entity_ip_address_version(entity_address) -> int:
    """
    Return ip version IP version. In case the IP is invalid an AWSWAFValidationException exception will be raised.
    :param address:  {str} ip address of version 4 or 6
    :return: {int} of IP Version. If IP address is invalid or ip version is not recognized -1 will be returned
                    raise AWSWAFValidationException if IP is invalid or IP version is not recognized
    """
    ip_version = get_ip_address_version(entity_address)
    if ip_version == -1:
        raise AWSWAFValidationException(
            f"Failed to validate IP or IP version for entity {entity_address}"
        )
    return ip_version


def mask_ip_address(address: str) -> str:
    """
    Mask given IP Version 4 or 6 address. If given address already masked return it.
    If IP Version 4 and not masked - mask with /32
    If IP Version 6 and not masked - mask with /128
    :param address: {str} ip address of version 4 or 6 to be masked
    :return: {str} masked ip address

    Note: function does not validate ip addresses
    """
    try:
        address = address.strip()
        ip_addr = ipaddress.ip_address(
            address
        )  # if masked/invalid this will raise an exception
        if ip_addr.version == 4:
            return address + consts.IPV4_MASK
        if ip_addr.version == 6:
            return address + consts.IPV6_MASK
    except Exception:
        return address


def unmask_ip_address(address: str) -> str:
    """
    Unmask given IP Version 4 or 6. If given address already unmasked return it.
    :param address: {str} ip address of version 4 or 6 to be unmaked
    :return: {str} unmasked ip address
    Note: function does not validate ip addresses
    """
    if address.rfind("/") != -1:
        return address[: address.rfind("/")]
    return address


def load_kv_csv_to_dict(kv_csv, param_name):
    """
    Load comma separated values of 'key':'value' represented as string to dictionary
    :param kv_csv: {str} of comma separated values of 'key':'value' represented as a string
    :param param_name: {str} name of the parameter
    :return: {dict} of key:value
            raise AWSWAFValidationException if failed to parse kv_csv
    """
    try:
        return {
            kv.split(":")[0].strip(): kv.split(":")[1].strip()
            for kv in kv_csv.split(",")
        }
    except Exception:
        raise AWSWAFValidationException(f"Failed to parse parameter {param_name}")


def get_ip_set_full_name(name: str, ip_version: int) -> str:
    """
    Get the full name of an IP set of pattern Siemplify_{Name}_{IP Version}
    :param name: {str} name of the IP Set
    :param ip_version: {int} the version of the IPs in the IP Set. Must be 4 or 6
    :return: {str} of full name IP Set
    """
    if ip_version == 4:
        return f"Siemplify_{name}_IPv4"
    return f"Siemplify_{name}_IPv6"


def is_action_approaching_timeout(siemplify_action: SiemplifyAction) -> bool:
    """
    Checks if approaching timeout for an action.
    :param siemplify_action: {SiemplifyAction} object
    :return: True if timeout of action approaches and adding logs to the siemplify action.
             otherwise return False.
    """
    if unix_now() >= siemplify_action.execution_deadline_unix_time_ms:
        siemplify_action.LOGGER.error(
            f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify_action.execution_deadline_unix_time_ms)}) has passed"
        )
        return True
    return False


def get_param_scopes(param_scope: str) -> list:
    """
    Returns list of mapped scopes of user input parameter scope. Values can be 'CloudFront' or 'Regional' or 'Both'.
    if 'CloudFront' is provided - will be returned ['CLOUDFRONT']
    if 'Regional' is provided - will be returned ['REGIONAL']
    if 'Both' is provided - will be returned ['REGIONAL','CLOUDFRONT']

    :param param_scope: {str} of user parameter 'Scope'. Values can be 'CloudFront' or 'Regional' or 'Both'
    :return: {[str]} list of mapped scope. Values can be ['CLOUDFRONT'] or ['REGIONAL'] or ['REGIONAL','CLOUDFRONT']
            raise AWSWAFValidationException if failed to validate scope.
    """
    if param_scope == consts.PARAM_BOTH_SCOPE:
        return [consts.REGIONAL_SCOPE, consts.CLOUDFRONT_SCOPE]
    elif param_scope not in consts.MAPPED_SCOPE:
        raise AWSWAFValidationException(f"Failed to validate scope {param_scope}")
    else:
        return [consts.MAPPED_SCOPE.get(param_scope)]

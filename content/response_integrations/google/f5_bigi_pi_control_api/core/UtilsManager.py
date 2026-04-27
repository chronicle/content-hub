from __future__ import annotations
import ipaddress
import requests
from .F5BIGIPiControlAPIExceptions import (
    F5BIGIPiControlAPIException,
    InvalidInputException,
)
from .constants import IPV4_MASK, IPV6_MASK, ALL_IPV6


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        if response.status_code == 404:
            raise InvalidInputException("Invalid input given.")
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise F5BIGIPiControlAPIException(
                f"{error_msg}: {error} {error.response.content}"
            )

        raise F5BIGIPiControlAPIException(
            f"{error_msg}: {error} {response.json().get('message') or response.content}"
        )


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


def mask_ip_address(address):
    """
    Mask given IP Version 4. If given address already masked return it.
    :param address: {str} ip address of version 4 that needs to be masked
    :return: {str} masked ip address
    """
    try:
        address = address.strip()
        ip_address = ipaddress.ip_address(
            address
        )  # if masked/invalid this will raise an exception

        if address == ALL_IPV6:
            return address

        if ip_address.version == 4:
            return address + IPV4_MASK

        if ip_address.version == 6:
            return address + IPV6_MASK

    except Exception:
        return address

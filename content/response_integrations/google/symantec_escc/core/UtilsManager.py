from __future__ import annotations
import requests


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


def convert_comma_separated_to_list(comma_separated):
    # type: (str) -> list
    """
    Convert comma-separated string to list
    @param comma_separated: String with comma-separated values
    @return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def convert_list_to_comma_string(values_list):
    # type: (list) -> str
    """
    Convert list to comma-separated string
    @param values_list: List of values
    @return: String with comma-separated values
    """
    return (
        ",".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )

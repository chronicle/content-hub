from __future__ import annotations
import requests
from .CloudflareExceptions import CloudflareException


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise CloudflareException(f"{error_msg}: {error} {error.response.content}")

        response_json = response.json()
        errors = response_json.get("errors", [])

        if errors:
            errors_message = "\n".join([err.get("message") for err in errors])
            error_chains = []
            for err in errors:
                error_chains.extend(err.get("error_chain", []))
            if error_chains:
                chains_message = "\n".join(
                    [chain.get("message") for chain in error_chains]
                )
                raise CloudflareException(f"{errors_message}: {chains_message}")
            raise CloudflareException(f"{errors_message}")
        else:
            raise CloudflareException(f"{error_msg}: {error} {response.content}")


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

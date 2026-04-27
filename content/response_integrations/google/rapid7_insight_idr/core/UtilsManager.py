from __future__ import annotations
import requests
from .Rapid7InsightIDRExceptions import NotFoundException, BadRequestException


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        if response.status_code == 404:
            raise NotFoundException(error)

        if response.status_code == 400:
            raise BadRequestException(error)

        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True

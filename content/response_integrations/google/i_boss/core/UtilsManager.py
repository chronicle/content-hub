from __future__ import annotations
import requests
from urllib.parse import urlparse


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}") from error

    return True


def strip_scheme(url):
    parsed = urlparse(url)
    scheme = f"{parsed.scheme}://"
    return parsed.geturl().replace(scheme, "", 1)

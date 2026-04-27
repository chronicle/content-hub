from __future__ import annotations
import requests
from dateutil.tz import tzoffset


def get_server_tzoffset(server_timezone):
    """
    get server timezone offset from utc
    :param server_timezone {str} UTC timezone offset
    :return: {tzoffset}
    """
    return tzoffset(None, float(server_timezone) * 60 * 60)


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

from __future__ import annotations
import datetime
import requests

UNIX_FORMAT = 1
DATETIME_FORMAT = 2
STORED_IDS_LIMIT = 3000


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise Exception(f"{error_msg}: {error} {error.response.content}")

    return True


def get_earliest_event_at_datetime(alerts):
    """
    Get event_at datetime from earliest alert in alert list
    :param alerts: The alerts list
    :return: {str} The earliest event_at
    """
    alerts.sort(
        key=lambda alert: datetime.datetime.strptime(
            alert.get("event_at"), "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    )
    return alerts[0].get("event_at")


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

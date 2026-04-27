from __future__ import annotations
import requests
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon import (
    WHITELIST_FILTER,
    BLACKLIST_FILTER,
    TIMEOUT_THRESHOLD,
    NUM_OF_MILLI_IN_SEC,
)
from .constants import SEVERITIES
from .SophosExceptions import SophosManagerError


GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1


def validate_api_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise SophosManagerError(f"{error_msg}: {error} {error.response.content}")

        api_error = response.json().get("error")
        error_message = (
            response.json().get("error", {}).get("code")
            if api_error
            else response.json().get("message")
        )

        raise SophosManagerError(
            f"{error_msg}: {error} {error_message or response.content}"
        )


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


# Two Actions are still using this (Endpoints actions)
def is_approaching_timeout(
    python_process_timeout, connector_starting_time, timeout_threshold=TIMEOUT_THRESHOLD
):
    """
    Check if a timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :param connector_starting_time: {int} The connector start unix time
    :param timeout_threshold: {int} Determines which part of the execution time is available for execution
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return (
        processing_time_ms
        > python_process_timeout * NUM_OF_MILLI_IN_SEC * timeout_threshold
    )


def pass_whitelist_filter(
    siemplify, whitelist_as_a_blacklist, model, model_key, whitelist=None
):
    # whitelist filter
    whitelist = whitelist or siemplify.whitelist
    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    model_value = getattr(model, model_key)
    model_values = model_value if isinstance(model_value, list) else [model_value]

    if whitelist:
        for value in model_values:
            if whitelist_filter_type == BLACKLIST_FILTER and value in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass blacklist filter.")
                return False

            if whitelist_filter_type == WHITELIST_FILTER and value not in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass whitelist filter.")
                return False

    return True


def pass_severity_filter(siemplify, alert, lowest_severity):
    # severity filter
    if lowest_severity:
        filtered_severities = (
            SEVERITIES[SEVERITIES.index(lowest_severity.lower()) :]
            if lowest_severity.lower() in SEVERITIES
            else []
        )
        if not filtered_severities:
            siemplify.LOGGER.info(
                'Severity is not checked. Invalid value provided for "Lowest Severity '
                'To Fetch" '
                "parameter. Possible values are: Low, Medium, High."
            )
        if filtered_severities and alert.severity.lower() not in filtered_severities:
            siemplify.LOGGER.info(
                f"Incident with severity: {alert.severity} did not pass filter. "
                f"Lowest severity to fetch is {lowest_severity}."
            )
            return False
    return True


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


def validated_limit(limit):
    if limit <= 0:
        raise Exception("Max Events To Return parameter should be positive")

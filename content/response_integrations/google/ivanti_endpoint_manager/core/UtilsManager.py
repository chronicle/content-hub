from __future__ import annotations
import requests
import xmltodict
import json
from .constants import FILTER_LOGIC
from soar_sdk.SiemplifyUtils import unix_now

GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
TIMEOUT_THRESHOLD = 0.9


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


def xml_to_json(xml_string):
    """
    Convert xml string to json
    :param xml_string: {str} xml string to convert
    :return: {dict} converted json
    """
    return json.loads(json.dumps(xmltodict.parse(xml_string)))


def filter_items(
    items, filter_key=None, filter_value=None, filter_logic=None, limit=None
):
    """
    Filter list of items
    :param items: {list} list of items to filter
    :param filter_key: {str} filter key that should be used for filtering
    :param filter_value: {str} filter value that should be used for filtering
    :param filter_logic: {str} filter logic that should be applied
    :param limit: {int} limit for items
    """
    if filter_key and filter_value:
        if filter_logic == FILTER_LOGIC.get("in_list") and isinstance(
            filter_value, list
        ):
            items = [
                item for item in items if getattr(item, filter_key) in filter_value
            ]

        if filter_logic == FILTER_LOGIC.get("equal"):
            items = [
                item for item in items if getattr(item, filter_key) == filter_value
            ]

        if filter_logic == FILTER_LOGIC.get("contains"):
            items = [
                item for item in items if filter_value in getattr(item, filter_key)
            ]

    return items[:limit] if limit else items


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
    )


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


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
    return processing_time_ms > python_process_timeout * 1000 * timeout_threshold


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)

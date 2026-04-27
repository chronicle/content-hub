from __future__ import annotations
import json
from .GoogleAlertCenterExceptions import (
    GoogleAlertCenterException,
    GoogleAlertCenterInvalidJsonException,
)
from .constants import SUCCESS_STATUSES
from TIPCommon import WHITELIST_FILTER, BLACKLIST_FILTER


def validate_response(
    response_info, content, sensitive_data_arr=None, error_msg="An error occurred"
):
    """
    Validate response
    :param response_info: {dict} The response info
    :param content: {dict} The response content
    :param sensitive_data_arr: {list} The list of sensitive data
    :param error_msg: {str} Default message to display on error
    """
    try:
        if (
            not isinstance(response_info, dict)
            or response_info.get("status", "") not in SUCCESS_STATUSES
        ):
            raise Exception

    except Exception:
        error_text = (
            content.get("error_description")
            if isinstance(content, dict) and content.get("error_description")
            else ""
        )

        if sensitive_data_arr:
            raise GoogleAlertCenterException(
                encode_sensitive_data(
                    str(f"{error_msg}: {error_text}"), sensitive_data_arr
                )
            )

        raise GoogleAlertCenterException(f"{error_msg}: {error_text}")

    return True


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


def parse_string_to_dict(string):
    """
    Parse json string to dict
    :param string: string to parse
    :return: {dict} parsed dict
    """
    try:
        return json.loads(string)
    except Exception:
        raise GoogleAlertCenterInvalidJsonException


def encode_sensitive_data(message, sensitive_data_arr):
    """
    Encode sensitive data
    :param message: {str} The error message which may contain sensitive data
    :param sensitive_data_arr: {list} The list of sensitive data
    :return: {str} The error message with encoded sensitive data
    """
    for sensitive_data in sensitive_data_arr:
        message = message.replace(sensitive_data, encode_data(sensitive_data))

    return message


def encode_data(sensitive_data):
    """
    Encode string
    :param sensitive_data: {str} String to be encoded
    :return: {str} Encoded string
    """
    if len(sensitive_data) > 1:
        return f"{sensitive_data[0]}...{sensitive_data[-1]}"

    return sensitive_data

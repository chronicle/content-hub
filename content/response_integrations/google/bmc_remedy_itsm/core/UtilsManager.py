from __future__ import annotations
import requests
import datetime
from soar_sdk.SiemplifyUtils import unix_now, convert_datetime_to_unix_time, utc_now
from .BMCRemedyITSMExceptions import (
    BMCRemedyITSMClientErrorException,
    BMCRemedyITSMServerErrorException,
    BMCRemedyITSMNotFoundException,
    BMCRemedyITSMJobException,
)
from .constants import ACTION_ITERATIONS_INTERVAL, ACTION_ITERATION_DURATION_BUFFER

UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        error_text = ""

        if response.status_code == 400 and isinstance(response.json(), list):
            for item in response.json():
                if item.get("messageNumber", "") == 307:
                    error_text += (
                        f"the following fields are mandatory: "
                        f"{convert_comma_separated_to_list(item.get('messageAppendedText', []) or [])} \n"
                    )
                else:
                    message_text = item.get("messageText", "") or ""
                    error_text += f"{message_text + ':' if message_text else ''} {item.get('messageAppendedText', '') or ''} \n"

            raise BMCRemedyITSMClientErrorException(error_text)

        if response.status_code == 404 and isinstance(response.json(), list):
            for item in response.json():
                if item.get("messageNumber", "") == 302:
                    raise BMCRemedyITSMNotFoundException(
                        f"{error_msg}: {error} {error.response.content}"
                    )
                else:
                    raise Exception(item.get("messageText", "") or "")

        if response.status_code == 500 and isinstance(response.json(), list):
            for item in response.json():
                message_text = item.get("messageText", "") or ""
                error_text += f"{message_text + ':' if message_text else ''} {item.get('messageAppendedText', '') or ''} \n"

                if item.get("messageNumber", "") in [1291053, 1291205]:
                    raise BMCRemedyITSMJobException(error_text)

            raise BMCRemedyITSMServerErrorException(error_text)

        if response.status_code == 404 and isinstance(response.json(), list):
            for item in response.json():
                message_text = item.get("messageText", "") or ""
                error_text += f"{message_text + ':' if message_text else ''} {item.get('messageAppendedText', '') or ''} \n"

            raise BMCRemedyITSMServerErrorException(error_text)

        raise Exception(f"{error_msg}: {error} {error.response.content}")

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


def get_names_from_customer(customer):
    """
    Get first and last names from customer string
    :param customer: {str} customer string
    :return: {tuple} first name and last name
    """
    names_list = [name.strip() for name in customer.split(" ")]

    if len(names_list) != 2:
        raise Exception(
            'Incorrect format for the "Customer" parameter. Customer needs to be provide in the format '
            '"{Last Name} {First Name}".'
        )

    return names_list[0], names_list[1]


def get_last_success_time(
    siemplify, offset_with_metric, time_format=DATETIME_FORMAT, print_value=True
):
    """
    Get last success time datetime
    :param siemplify: {siemplify} Siemplify object
    :param offset_with_metric: {dict} metric and value. Ex {'hours': 1}
    :param time_format: {int} The format of the output time. Ex DATETIME, UNIX
    :param print_value: {bool} Whether log the value or not
    :return: {time} If first run, return current time minus offset time, else return timestamp from file
    """
    last_run_timestamp = siemplify.fetch_timestamp(datetime_format=True)
    offset = datetime.timedelta(**offset_with_metric)
    current_time = utc_now()
    # Check if first run
    datetime_result = (
        current_time - offset
        if current_time - last_run_timestamp > offset
        else last_run_timestamp
    )
    unix_result = convert_datetime_to_unix_time(datetime_result)
    if print_value:
        siemplify.LOGGER.info(
            f"Last success time. Date time:{datetime_result}. Unix:{unix_result}"
        )
    return unix_result if time_format == UNIX_FORMAT else datetime_result


def is_async_action_timeout(siemplify):
    """
    Check if async action timeout approaching
    :param siemplify: SiemplifyAction object.
    :return: {bool} True - if timeout approaching, False - otherwise.
    """
    return (
        unix_now() + ACTION_ITERATION_DURATION_BUFFER + ACTION_ITERATIONS_INTERVAL
        >= siemplify.execution_deadline_unix_time_ms
    )

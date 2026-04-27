from __future__ import annotations
import requests
import datetime
from bs4 import BeautifulSoup
from .SumoLogicCloudSIEMExceptions import (
    SumoLogicCloudSIEMException,
    InvalidTimeException,
)
from soar_sdk.SiemplifyUtils import convert_string_to_datetime
from dateutil.relativedelta import relativedelta
from .constants import TIME_FORMAT, TIMEFRAME_MAPPING

WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    json_error, api_error = None, None
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            api_error = BeautifulSoup(response.content, "html.parser").p.text
        except Exception:
            try:
                json_error = response.json().get("errors", [])[0].get("message")
            except Exception:
                raise SumoLogicCloudSIEMException(
                    f"{error_msg}: {error} {error.response.content}"
                )

        if json_error:
            raise SumoLogicCloudSIEMException(f"{json_error}")
        raise SumoLogicCloudSIEMException(
            f"{error_msg}: {error} {api_error or response.content}"
        )


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


def datetime_to_rfc3339(datetime_obj: datetime.datetime) -> str:
    """
    Convert datetime object to RFC 3999 representation
    :param datetime_obj: {datetime.datetime} The datetime object to convert
    :return: {str} The RFC 3999 representation of the datetime
    """
    return datetime_obj.strftime(TIME_FORMAT)


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


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def get_timestamps_from_range(range_string, alert_start_time=None, alert_end_time=None):
    """
    Get start and end time timestamps from range
    :param range_string: {str} Time range string
    :param alert_start_time: {str} Start time of the alert
    :param alert_end_time: {str} End time of the alert
    :return: {tuple} start and end time timestamps
    """
    now = datetime.datetime.utcnow()
    timeframe = TIMEFRAME_MAPPING.get(range_string)

    if isinstance(timeframe, dict):
        start_time, end_time = now - datetime.timedelta(**timeframe), now
    elif timeframe == TIMEFRAME_MAPPING.get("Last Week"):
        start_time, end_time = now - datetime.timedelta(weeks=1), now
    elif timeframe == TIMEFRAME_MAPPING.get("Last Month"):
        start_time, end_time = now - relativedelta(months=1), now
    elif timeframe == TIMEFRAME_MAPPING.get("5 Minutes Around Alert Time"):
        start_time, end_time = alert_start_time - datetime.timedelta(
            minutes=5
        ), alert_end_time + datetime.timedelta(minutes=5)
    elif timeframe == TIMEFRAME_MAPPING.get("30 Minutes Around Alert Time"):
        start_time, end_time = alert_start_time - datetime.timedelta(
            minutes=30
        ), alert_end_time + datetime.timedelta(minutes=30)
    elif timeframe == TIMEFRAME_MAPPING.get("1 Hour Around Alert Time"):
        start_time, end_time = alert_start_time - datetime.timedelta(
            hours=1
        ), alert_end_time + datetime.timedelta(hours=1)
    else:
        return None, None

    return datetime_to_rfc3339(start_time), datetime_to_rfc3339(end_time)


def get_timestamps(
    range_string,
    start_time_string=None,
    end_time_string=None,
    alert_start_time=None,
    alert_end_time=None,
):
    """
    Get start and end time timestamps
    :param range_string: {str} Time range string
    :param start_time_string: {str} Start time
    :param end_time_string: {str} End time
    :param alert_start_time: {str} Start time of the alert
    :param alert_end_time: {str} End time of the alert
    :return: {tuple} start and end time timestamps
    """
    start_time, end_time = get_timestamps_from_range(
        range_string, alert_start_time, alert_end_time
    )
    current_time_rfc3339 = datetime_to_rfc3339(datetime.datetime.utcnow())

    if not start_time and start_time_string:
        start_time = datetime_to_rfc3339(convert_string_to_datetime(start_time_string))

    if not end_time and end_time_string:
        end_time = datetime_to_rfc3339(convert_string_to_datetime(end_time_string))

    if not start_time:
        raise InvalidTimeException

    if not end_time or end_time > current_time_rfc3339:
        end_time = current_time_rfc3339

    if start_time > end_time:
        raise Exception('"End Time" should be later than "Start Time"')

    return start_time, end_time

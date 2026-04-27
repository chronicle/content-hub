from __future__ import annotations
import datetime
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, utc_now

UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    # type: (str, str, bool) -> list
    """
    String to multi value.
    @param string_value: {str} String value to convert multi value.
    @param delimiter: {str} Delimiter to extract multi values from single value string.
    @param only_unique: {bool} include only unique values
    """
    if not string_value:
        return []
    values = [
        single_value.strip()
        for single_value in string_value.split(delimiter)
        if single_value.strip()
    ]
    if only_unique:
        seen = set()
        return [value for value in values if not (value in seen or seen.add(value))]
    return values


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

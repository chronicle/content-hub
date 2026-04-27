from __future__ import annotations
import os

from .constants import DATETIME_FORMAT, UNIX_FORMAT
from soar_sdk.SiemplifyUtils import utc_now, convert_datetime_to_unix_time
import datetime
import arrow


# Move to TIPCommon
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
            f"Last success time. Date time: {datetime_result}. Unix: {unix_result}"
        )

    return unix_result if time_format == UNIX_FORMAT else datetime_result


def get_days_back(last_run_timestamp):
    """
    Get amount of days back using last run timestamp
    :param last_run_timestamp: The last run timestamp
    :return: {int} The amount of days back
    """
    return (
        arrow.utcnow().datetime - arrow.get(last_run_timestamp / 1000).datetime
    ).days


def read_offset(siemplify, file_name="offset.txt"):
    """
    Read stored offset from offset txt file
    :param siemplify: {Siemplify} Siemplify object.
    :param file_name: {str} The name of the offset file
    :return: {int} The offset
    """
    offset_file_path = os.path.join(siemplify.run_folder, file_name)

    if not os.path.exists(offset_file_path):
        return 0

    try:
        with open(offset_file_path, "rb") as f:
            return int(f.read())
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to read offset file: {e}")
        siemplify.LOGGER.exception(e)
        return 0


def write_offset(siemplify, offset, file_name="offset.txt"):
    """
    Write offset to the offset txt file
    :param siemplify: {Siemplify} Siemplify object.
    :param offset: The offset to write to the file
    :param file_name: {str} The name of the offset file
    :return: {bool}
    """
    try:
        offset_file_path = os.path.join(siemplify.run_folder, file_name)

        if not os.path.exists(os.path.dirname(offset_file_path)):
            os.makedirs(os.path.dirname(offset_file_path))

        with open(offset_file_path, "wb") as f:
            f.write(f"{offset}")

    except Exception as e:
        siemplify.LOGGER.error(f"Failed writing offset to offset file, ERROR: {e}")
        siemplify.LOGGER.exception(e)

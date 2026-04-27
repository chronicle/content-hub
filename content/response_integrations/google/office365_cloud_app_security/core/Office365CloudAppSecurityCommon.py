from __future__ import annotations
from soar_sdk.SiemplifyUtils import utc_now
import datetime


class Office365CloudAppSecurityCommon:
    def __init__(self, siemplify_logger):
        self.siemplify_logger = siemplify_logger

    @staticmethod
    def validate_timestamp(last_run_timestamp, offset_in_hours):
        """
        Validate timestamp in range
        :param last_run_timestamp: {datetime} last run timestamp
        :param offset: {datetime} last run timestamp
        :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
        """
        current_time = utc_now()
        # Check if first run
        if current_time - last_run_timestamp > datetime.timedelta(
            hours=offset_in_hours
        ):
            return current_time - datetime.timedelta(hours=offset_in_hours)
        else:
            return last_run_timestamp

    @staticmethod
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

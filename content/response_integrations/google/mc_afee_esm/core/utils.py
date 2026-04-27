from __future__ import annotations
from typing import Tuple
import datetime

from .constants import QUERY_TIME_FORMAT


# Move to TIP Common
def get_timestamps(start_time_string: str, end_time_string: str) -> Tuple[str, str]:
    """
    Get start and end time timestamps
    Args:
        start_time_string (str): Start time
        end_time_string (str): End time
    Returns:
        (tuple): start and end time
    """
    if not start_time_string:
        raise Exception(
            '"Start Time" should be provided, when "Custom" is selected in "Time Range" parameter.'
        )

    if not end_time_string:
        end_time_string = datetime.datetime.utcnow().strftime(QUERY_TIME_FORMAT)

    if start_time_string > end_time_string:
        raise Exception('"End Time" should be later than "Start Time"')

    return start_time_string, end_time_string

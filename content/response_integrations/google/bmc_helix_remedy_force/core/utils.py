from __future__ import annotations
from .constants import ASYNC_ACTION_TIMEOUT_THRESHOLD_MS


def is_approaching_timeout(action_start_time, python_process_timeout):
    """
    Check if a timeout is approaching.
    :param action_start_time: {int} Action start time
    :param python_process_timeout: {int} The python process timeout
    :return: {bool} True if timeout is close, False otherwise
    """
    return (
        action_start_time > python_process_timeout - ASYNC_ACTION_TIMEOUT_THRESHOLD_MS
    )

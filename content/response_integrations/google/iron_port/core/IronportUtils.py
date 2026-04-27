from __future__ import annotations
from .IronportConstants import ASYNC_RUN_TIMEOUT_MS, ITERATION_DURATION_BUFFER
from soar_sdk.SiemplifyUtils import unix_now


def is_script_approaching_timeout(action_start_time):
    """
    Check if script timeout approaching
    :param action_start_time: {int} timeout in milliseconds
    :return: {bool} True - if timeout approaching, False - otherwise.
    """
    return (
        unix_now()
        >= action_start_time + ASYNC_RUN_TIMEOUT_MS - ITERATION_DURATION_BUFFER
    )

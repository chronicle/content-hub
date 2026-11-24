from __future__ import annotations

import json
import concurrent.futures
from typing import Any
from google_cloud_recommender.core import exceptions
from bs4 import BeautifulSoup

from TIPCommon.base.utils import validate_manager
from TIPCommon.consts import TIMEOUT_THRESHOLD
from TIPCommon.rest.gcp import validate_impersonation
from TIPCommon.smp_time import unix_now, is_approaching_timeout
from google_cloud_recommender.core import consts


def validate_response(
    response_info: dict,
    content: dict | str,
    sensitive_data_arr=None,
    error_msg="An error occurred",
):
    """
    Validate response
    Args:
        response_info (dict): The response info
        content (dict): The response content
        sensitive_data_arr (list): The list of sensitive data
        error_msg (str): Default message to display on error
    Returns:
        (bool)
    Raises:
        GoogleCloudRecommenderError: if there is any error
    """
    status_code = int(response_info.get("status", ""))
    if 200 <= status_code < 400:
        return

    try:
        content = json.loads(content)
    except json.decoder.JSONDecodeError:
        pass

    validate_impersonation(content)

    message = get_error_message_from_response(status_code, content, error_msg)

    if sensitive_data_arr:
        message = encode_sensitive_data(message, sensitive_data_arr)

    if status_code == consts.NOT_FOUND_STATUS:
        raise exceptions.GoogleCloudRecommenderStatusNotFoundError(f"{message}")
    elif status_code == consts.PERMISSION_DENIED_STATUS:
        raise exceptions.GoogleCloudRecommenderPermissionsDeniedError(f"{message}")

    raise exceptions.GoogleCloudRecommenderError(f"{message}")


def get_error_message_from_response(
    status_code: int, content: bytes | dict, error_msg: str = "An error occurred"
) -> str:
    """Gets the error message from the response content

    Args:
        content: Response content
        error_msg: Generic error message to be applied at the beginning of each
        error message
    Returns:    An error message
    """
    if isinstance(content, dict):
        message = content.get("error", {}).get("message")
        error_text = message
    else:
        error_text = BeautifulSoup(content, "html.parser").p.text

    return f"{error_msg}: {error_text}\nResponse Status Code: {status_code}"


def encode_sensitive_data(message, sensitive_data_arr):
    """
    Encode sensitive data
    Args:
        message: (str): The error message which may contain sensitive data
        sensitive_data_arr: (list): The list of sensitive data
    Returns:
        (str): The error message with encoded sensitive data
    """
    for sensitive_data in sensitive_data_arr:
        message = message.replace(sensitive_data, encode_data(sensitive_data))

    return message


def encode_data(sensitive_data):
    """
    Encode string
    Args:
        sensitive_data: (str): String to be encoded
    Returns:
        (str): Encoded string
    """
    if len(sensitive_data) > 1:
        return f"{sensitive_data[0]}...{sensitive_data[-1]}"

    return sensitive_data


def multithread_execution(
    f,
    logger,
    max_workers: int,
    python_process_timeout: int,
    action_start_time: int,
    args: list[list[Any]],
):
    """Execute multiple threads of function f for args while keeping max_workers amount and respecting timeouts.

    Args:
        f: function to execute
        logger: Logger
        max_workers: Max amount of workers to spawn.
        python_process_timeout: Python process timeout
        action_start_time: Start time for action in UNIX
        args: List of Args provided for executing the function f. [[a, b], [b]]

    Returns:
        Output of executing f on args
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    submitted_funcs = []
    for _args in args:
        submitted_funcs.append(executor.submit(f, *_args))

    processing_time = (unix_now() - action_start_time) / consts.NUM_OF_MILLI_IN_SEC
    concurrent_timeout = (python_process_timeout - processing_time) * TIMEOUT_THRESHOLD
    execution_results = []

    try:
        for submitted_func in concurrent.futures.as_completed(
            submitted_funcs, timeout=concurrent_timeout
        ):

            execution_results.append(submitted_func.result())
            if is_approaching_timeout(
                action_start_time,
                python_process_timeout,
                timeout_threshold=TIMEOUT_THRESHOLD,
            ):
                executor.shutdown(wait=False)
                raise TimeoutError("Timeout is approaching. ")

    except TimeoutError:
        logger.info("Timeout is approaching. Script will gracefully exit.")

    return execution_results


def test_service_connectivity(
    action_object: Any, service_name: str, manager: Any
) -> None:
    """Test connectivity for recommender and resource manager service.

    Args:
        action_object (Any): Action object to set service_name and to use
        logger.
        service_name (str): service name "Google Cloud Recommender" or
        "Google Cloud Resource Manager"

        manager (Any): GoogleCloudRecommenderManager, GoogleCloudResourceManager

    Raises:
        err: Raise error from validate_response method.
    """
    try:
        action_object.service_name = service_name
        action_object.logger.info("Validating manager is not None")
        validate_manager(manager)

        action_object.logger.info(f"Testing connectivity for {service_name} service")
        manager.test_connectivity()
        action_object.logger.info(f"Successfully connected to {service_name} service")
    except Exception as err:
        action_object.error_output_message = (
            f"Failed to connect to the {service_name} service!"
        )
        raise err from err

from __future__ import annotations
import os
import hashlib
from typing import BinaryIO, List, Dict
import requests
from requests import Response
from intezer.core import constants
from intezer.core import exceptions


def validate_response(response: Response, error_msg: str = "An error occurred") -> None:
    """Validate the response of an API request

    Args:
        response: The response info
        error_msg: Default message to display in case of an error
    Raises:
        IntezerManagerError: if there is any error
    """
    try:
        if response.status_code == constants.API_LIMIT_ERROR:
            raise exceptions.IntezerAPILimitError("Reached API request limitation")

        if response.status_code == constants.API_NOT_FOUND:
            raise exceptions.IntezerNotFoundError(
                "Analysis was not found for the requested item"
            )

        if response.status_code == constants.API_BAD_REQUEST:
            raise exceptions.IntezerBadRequestError(response.json()["error"])

        if response.status_code in constants.API_USER_INPUT_ERROR:
            raise exceptions.IntezerUserInputError

        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            response.json()

            if response.status_code == constants.API_NOT_FOUND:
                raise exceptions.IntezerNotFoundError(
                    response.json().get("error", {}).get("message", "")
                )

            raise exceptions.IntezerManagerError(
                f"{error_msg}: {error} "
                f"{response.json().get('error', {}).get('message', response.content)}"
            )

        except exceptions.IntezerManagerError:
            raise

        except:
            raise exceptions.IntezerManagerError(
                f"{error_msg}: {error} {response.content}"
            ) from error


def is_valid_file_path(file_path: str) -> bool:
    """Check if a file path is valid

    Args:
        file_path: The path of file to check
    Returns:
        True if the file path is valid
    """

    if not os.path.exists(file_path):
        raise exceptions.IntezerNotFoundError(f"File {file_path} doesn't exist.")
    return True


def get_id_from_response(response: Response) -> str:
    """Get the id from the analysis result

    Args:
        response: The response from the analysis
    Returns:
        The id of the analysis result
    """
    return response.json()["result_url"].split("/")[-1]


def parse_file_from_file_stream(alert_stream: BinaryIO) -> str:
    """Parse the file alert id from file stream

    Args:
        alert_stream: The alert stream of the file
    Returns:
        The alert id of the file stream
    """
    try:
        return hashlib.sha256(alert_stream.read()).hexdigest()
    finally:
        alert_stream.seek(0)


def remove_duplicate_dict_from_list(data: List[Dict]) -> List[Dict]:
    """Removes duplicate dictionaries from a list

    Args:
        data: The list containing duplicate dictionaries
    Returns:
        The list containing unique dictionaries
    """
    empty_list = []

    for item in data:
        if item not in empty_list:
            empty_list.append(item)
    return empty_list


def remove_pending_items(
    data: List[Dict], in_progress_status: str, queued_status: str, status_key: str
) -> List[Dict]:
    """Remove pending items from the final list

    Args:
        data: The list containing pending items
        in_progress_status: In progress status
        queued_status: Queued status
        status_key: Status key
    Returns:
        The list containing only completed items
    """
    for d in data:
        if d[status_key] in (in_progress_status, queued_status):
            data.remove(d)
    return data

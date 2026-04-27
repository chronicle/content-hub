from __future__ import annotations
import requests
import os
from .constants import NOT_FOUND_CODE, INVALID_PARAMETERS_CODE
from .exceptions import (
    CheckpointManagerError,
    CheckpointManagerBadRequestException,
    CheckpointManagerNotFoundException,
)


def validate_response(response):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        if response.status_code == NOT_FOUND_CODE:
            raise CheckpointManagerNotFoundException(error)
        if response.status_code == INVALID_PARAMETERS_CODE:
            raise CheckpointManagerBadRequestException(error)
        raise CheckpointManagerError(error)


def save_attachment(path, name, content):
    """
    Save attachment to local path
    :param path: {str} Path of the folder, where files should be saved
    :param name: {str} File name to be saved
    :param content: {str} File content
    :return: {str} Path to the downloaded files
    """
    # Create path if not exists
    if not os.path.exists(path):
        os.makedirs(path)
    # File local path
    local_path = os.path.join(path, name)
    with open(local_path, "wb") as file:
        file.write(content)
        file.close()

    return local_path

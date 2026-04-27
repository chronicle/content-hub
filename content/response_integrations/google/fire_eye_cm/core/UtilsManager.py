from __future__ import annotations
import base64
import datetime
import os
import defusedxml.ElementTree as ET
from typing import Optional

import requests

from .FireEyeCMConstants import (
    PROVIDER_NAME,
    ENTITIES_FILE_NAME,
    API_NOT_FOUND,
    API_BAD_REQUEST,
)
from .FireEyeCMExceptions import (
    FireEyeCMNotFoundException,
    FireEyeCMException,
    FireEyeCMValidationException,
    FireEyeCMDownloadFileError,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import utc_now


UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def validate_timestamp(last_run_timestamp, offset_in_hours):
    """
    Validate timestamp in range
    :param last_run_timestamp: {datetime} last run timestamp
    :param offset_in_hours: {int} backward hours count
    :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
    """
    current_time = utc_now()
    # Check if first run
    if current_time - last_run_timestamp > datetime.timedelta(hours=offset_in_hours):
        return current_time - datetime.timedelta(hours=offset_in_hours)
    else:
        return last_run_timestamp


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {str} Default message to display on error
    """
    try:
        if response.status_code == API_NOT_FOUND:
            raise FireEyeCMNotFoundException(f"Not Found in {PROVIDER_NAME}")

        if response.status_code == API_BAD_REQUEST:
            raise FireEyeCMValidationException(
                response.json().get("fireeyeapis", {}).get("message") or error_msg
            )

        response.raise_for_status()

    except requests.HTTPError as error:

        if response.text:
            try:
                root = ET.fromstring(response.text)
                message = root.find("message")

                if message is not None:
                    raise FireEyeCMException(message.text or response.text)

                raise FireEyeCMException(response.text)

            except Exception:
                try:
                    error_msg = response.json().get("fireeyeapis", {}).get(
                        "message"
                    ) or response.json().get("entity", {}).get("message")
                    raise FireEyeCMException(
                        "{error_msg}: {error} {text}".format(
                            error_msg=error_msg, error=error, text=error_msg
                        )
                    )

                except FireEyeCMException:
                    raise

                except Exception:
                    raise FireEyeCMException(
                        "{error_msg}: {error} {text}".format(
                            error_msg=error_msg, error=error, text=response.text
                        )
                    )

        raise FireEyeCMException(
            "{error_msg}: {error} {text}".format(
                error_msg=error_msg, error=error, text=error.response.text
            )
        )

    return True


def create_entities_file(siemplify, identifier):
    """
    Write identifiers to the identifiers file
    :param siemplify: {Siemplify} Siemplify object.
    :param identifier: {str} The entity identifier to write to the file
    :return: {str} File path
    """
    try:
        file_path = os.path.join(
            siemplify.run_folder,
            (
                ENTITIES_FILE_NAME.format(
                    base64.b64encode(identifier.encode()).decode()
                )
            ).replace("=", ""),
        )
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w") as f:
            try:
                f.write(identifier)
            except:
                # Move seeker to start of the file
                f.seek(0)
                # Empty the content of the file (the partially written content that was written before the exception)
                f.truncate()
                # Write an empty string to the data file
                f.write("")
                raise
        return file_path
    except Exception as err:
        siemplify.LOGGER.error(
            "Failed writing identifier to the file, ERROR: {0}".format(str(err))
        )
        siemplify.LOGGER.exception(err)
        return None


def create_custom_rules_file(siemplify: SiemplifyAction, file_path: str, rule: str):
    """
    Write rule to rules file
    :param siemplify: {SiemplifyAction} SiemplifyAction object
    :param file_path: {str} The file path to create the file
    :param rule: {str} the rule to add to the custom rules file
    """
    try:
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w+") as f:
            try:
                f.write(rule)
            except:
                # Move seeker to start of the file
                f.seek(0)
                # Empty the content of the file (the partially written content that was written before the exception)
                f.truncate()
                # Write an empty string to the data file
                f.write("")
                raise
        return file_path
    except Exception as err:
        siemplify.LOGGER.error(f"Failed writing rule {rule} to the file, ERROR: {err}")
        siemplify.LOGGER.exception(err)


def remove_empty_kwargs(kwargs: dict) -> dict:
    """
    Remove keys from dictionary that has the value None. Note - empty iterables will not be removed
    :param kwargs: key value arguments
    :return: dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def save_artifacts_to_file(
    response: requests.models.Response,
    download_path: str,
    overwrite: Optional[bool] = False,
):
    """
    Save raw data to a zip in defined path.
    :param response: {requests.models.Response} Downloaded response.
    :param download_path: {str} Path to save the files.
    :param overwrite: {bool} True if overwrite existing file, otherwise False
    :return: True if successful, exception otherwise
    """
    try:
        if not os.path.exists(download_path) or overwrite:
            with open(download_path, "wb") as f:
                for chunk in response.iter_content():
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        raise FireEyeCMDownloadFileError(e)


def append_artifacts_to_file(response: requests.models.Response, download_path: str):
    """
    Append raw data to a defined path.
    :param response: {requests.models.Response} Downloaded response.
    :param download_path: {str} Path to append the file
    :return: True if successful, exception otherwise
    """
    try:
        with open(download_path, "ab") as f:
            for chunk in response.iter_content():
                f.write(chunk)
        return True
    except Exception as e:
        raise FireEyeCMDownloadFileError(e)

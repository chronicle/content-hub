from __future__ import annotations
import os
from soar_sdk.SiemplifyUtils import unix_now
from .constants import DEFAULT_RESULTS_LIMIT

GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1
TIMEOUT_THRESHOLD = 0.9


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def is_approaching_timeout(
    python_process_timeout, connector_starting_time, timeout_threshold=0.9
):
    """
    Check if a timeout is approaching.
    :param python_process_timeout: {int} The python process timeout
    :param connector_starting_time: {int} The connector start unix time
    :param timeout_threshold: {int} Determines which part of the execution time is available for execution
    :return: {bool} True if timeout is close, False otherwise
    """
    processing_time_ms = unix_now() - connector_starting_time
    return processing_time_ms > python_process_timeout * 1000 * timeout_threshold


def get_validated_limit(number, number_replacer=DEFAULT_RESULTS_LIMIT):
    if number <= 0:
        return number_replacer
    return number


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
    )


class PathIsNotWritable(Exception):
    pass


def validate_local_path(local_path):
    try:
        tmp_file_name = "tmp_file"
        save_attachment(local_path, tmp_file_name, b"")
        os.remove(os.path.join(local_path, tmp_file_name))
    except Exception as e:
        raise PathIsNotWritable(f'Path "{local_path}" is not writable. {e}')


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


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :param only_unique: {bool} include only unique values
    :return: {dict} fixed dictionary.
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


def is_all_filenames_with_folders(filenames):
    for filename in filenames:
        if "/" not in filename:
            return False

    return True

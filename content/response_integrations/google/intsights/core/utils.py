from __future__ import annotations
import os
import csv
from .exceptions import IntsightsAlreadyExistsError
import arrow


def save_file(path, name, content, overwrite):
    """
    Save file to local path
    :param path: {str} Path of the folder, where files should be saved
    :param name: {str} File name to be saved
    :param content: {str} File content
    :param overwrite: {bool} Specifies if overwrite the existing file or not
    :return: {str} Path to the downloaded file
    """
    # Raise an error if path does not exist
    if not os.path.exists(path):
        raise Exception("Specified path doesn't exist.")

    # File local path
    local_path = os.path.join(path, name)
    local_path = f"{local_path}{'.csv'}"

    if not overwrite and os.path.exists(local_path):
        raise IntsightsAlreadyExistsError(local_path)

    with open(local_path, "w") as file:
        writer = csv.writer(file)
        for line in content.iter_lines():
            writer.writerow(line.decode("utf-8").split(","))

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


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def validate_timestamp(last_run_timestamp, offset):
    """
    Validate timestamp in range
    :param last_run_timestamp: {datetime} last run timestamp
    :param offset: {datetime} last run timestamp
    :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
    """
    current_time = arrow.utcnow()

    # Check if first run
    if current_time.shift(days=-offset) > arrow.get(last_run_timestamp / 1000):
        return current_time.shift(days=-offset).int_timestamp * 1000
    else:
        return last_run_timestamp

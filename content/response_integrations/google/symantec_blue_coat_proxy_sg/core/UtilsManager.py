from __future__ import annotations
import re
from .constants import (
    DEFAULT_PORT,
    LINE_DELIMITERS,
    SKIP_ROWS_NUMBER,
    KEY_VALUE_DELIMITER,
    PARENT_KEY_PATTERN,
    CUSTOM_LIST_DELIMITER,
)


def validate_response():
    pass


def split_address(address):
    """
    Split address to separate ip and port
    :param address: {str} address to split
    :return: {(str, int)} ip address and port
    """
    if ":" in address:
        split = address.split(":")
        address = split[0]
        port = int(split[1])
        return address, port
    else:
        return address, DEFAULT_PORT


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def parse_command_output(output):
    """
    Parse command output
    :param output: {str} command output to parse
    :return: {dict} parsed dictionary
    """
    output = output.strip(LINE_DELIMITERS)
    output_mockup = construct_output_mockup(output)
    output_dict = {}

    if output_mockup:
        for key, value in output_mockup.items():
            output_dict[key] = convert_string_to_dict(value)
    else:
        output_dict = convert_string_to_dict(output, SKIP_ROWS_NUMBER)

    return output_dict


def construct_output_mockup(output):
    """
    Construct output mockup
    :param output: {str} output string
    :return: {dict} output mockup dictionary
    """
    parent_key_regex_pattern = PARENT_KEY_PATTERN.format("(.*?)")
    parent_keys = [
        PARENT_KEY_PATTERN.format(parent_key)
        for parent_key in re.findall(parent_key_regex_pattern, output)
    ]
    mockup = {}

    for parent_key in parent_keys:
        start = output.find(parent_key) + len(parent_key)
        end = (
            output.find(parent_keys[parent_keys.index(parent_key) + 1])
            if parent_keys.index(parent_key) + 1 < len(parent_keys)
            else len(output)
        )

        mockup[re.search(parent_key_regex_pattern, parent_key).group(1)] = output[
            start:end
        ]

    return mockup


def convert_string_to_dict(string, skip_rows_number=0):
    """
    Convert string to dict
    :param string: {str} string to convert
    :param skip_rows_number: {int} number of rows to skip
    :return: {dict} convert dictionary
    """
    rows = string.split(LINE_DELIMITERS)[skip_rows_number:]
    key_value_list = []
    output_dict = {}

    for row in rows:
        if not row:
            continue

        if KEY_VALUE_DELIMITER in row:
            key_value_list.append(row)
        elif key_value_list:
            key_value_list[-1] = key_value_list[-1] + row + CUSTOM_LIST_DELIMITER

    for key_value in key_value_list:
        key, value = key_value.split(KEY_VALUE_DELIMITER, 1)
        output_dict[key.strip()] = (
            convert_comma_separated_to_list(value)
            if CUSTOM_LIST_DELIMITER in value
            else value.replace("\t", "").strip()
        )

    return output_dict


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [
            item.strip()
            for item in comma_separated.split(CUSTOM_LIST_DELIMITER)
            if item.strip()
        ]
        if comma_separated
        else []
    )


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

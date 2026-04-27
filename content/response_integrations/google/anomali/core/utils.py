from __future__ import annotations
import re
from .constants import SEVERITY_MAPPING
from .exceptions import AnomaliNotFoundException
from .constants import EMAIL_REGEX, EMAIL_TYPE
from soar_sdk.SiemplifyDataModel import EntityTypes


class LOGGER:
    def __init__(self, logger):
        self.logger = logger

    def info(self, msg):
        if self.logger:
            self.logger.info(msg)


def string_to_multi_value(string_value, delimiter=",", only_unique=False):
    """
    String to multi value.
    :param string_value: {str} String value to convert multi value.
    :param delimiter: {str} Delimiter to extract multi values from single value string.
    :param only_unique: {bool} include only uniq values
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


def is_valid_email(user_name):
    """
    Check if the user_name is valid email.
    :param user_name: {str} User name
    :return: {bool} True if valid email, else False
    """
    return bool(re.search(EMAIL_REGEX, user_name))


def get_existing_list(dictionary, key):
    if not dictionary.get(key):
        dictionary[key] = []

    return dictionary[key]


def extend_list(dictionary, key, extend_with):
    if extend_with:
        get_existing_list(dictionary=dictionary, key=key).extend(extend_with)


def get_entity_type(entity):
    """
    Helper function for getting entity type
    :param entity: entity from which function will get type
    :return: {str} entity type
    """
    if entity.entity_type == EntityTypes.USER and is_valid_email(
        get_entity_original_identifier(entity)
    ):
        return EMAIL_TYPE

    return entity.entity_type


def get_severity_score(severity):
    severity_score = SEVERITY_MAPPING.get(severity.lower())

    if severity_score is not None:
        return severity_score

    raise AnomaliNotFoundException(f'Invalid severity type "{severity}" is provided.')

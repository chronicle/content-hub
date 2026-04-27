from __future__ import annotations
import re
import datetime
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from soar_sdk.SiemplifyDataModel import EntityTypes
from .constants import (
    TIME_FORMAT,
    OBSERVABLE_TIME_FORMAT,
    EMAIL_REGEX,
    EMAIL_TYPE,
    ASSOCIATION_TYPE_TO_ENTITY,
)


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def convert_string_to_unix_time(time_str):
    """
    Convert string time of format 2020-03-15T04:24:55.428496 or 2020-03-15T04:24:55.428496Z to unix time in ms
    :param time_str: {str} time in format '2020-03-15T04:24:55.428496' or '2020-03-15T04:24:55.428496Z'
    :return: {int} unix time in ms
    """
    try:
        dt = datetime.datetime.strptime(time_str, TIME_FORMAT)
        return convert_datetime_to_unix_time(dt)
    except Exception as e:
        pass

    try:
        dt = datetime.datetime.strptime(time_str, OBSERVABLE_TIME_FORMAT)
        return convert_datetime_to_unix_time(dt)
    except Exception as e:
        pass
    return 1


def as_html_link(link):
    return f"""<a href="{link}" target="_blank">{link}</a>"""


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


def is_valid_email(user_name):
    """
    Check if the user_name is valid email.
    :param user_name: {str} Users name
    :return: {bool} True if valid email, else False
    """
    return bool(re.search(EMAIL_REGEX, user_name))


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


def datetime_to_string(datatime_obj: datetime.datetime):
    """
    Convert datetime object to 2020-03-15T04:24:55.428496 time format
    :param datatime_obj: {datetime.datetime} The datetime object to convert
    :return: {str} The string representation of the datetime in format 2020-03-15T04:24:55.428496
    """
    return datatime_obj.strftime(TIME_FORMAT)


def append_association_type_to_entities(entities, mapper, type, entity_identifier):
    """
    Append entity object to entities list. Mapper maps supported entities to True
    :param entities: {list} list of entities to append the new entity object
    :param mapper: {dict} maps the type to bool. If True the type is supported
    :param type: {str} the type of the mapped value
    :param entity_identifier: {str} the identifier of the entity to append
    :return: {list} list of updated entities
    """
    if mapper.get(type):
        entities.append(
            {
                "identifier": entity_identifier,
                "type": ASSOCIATION_TYPE_TO_ENTITY.get(type),
            }
        )
    return entities


def get_max_dict_value_size(dictionary):
    """
    Return the maximum length of a value in a dictionary
    :param dictionary: {dict} dictionary. Values should be iterables not string
    :return: {int} maximum length of a value in a dictionary
    """
    return max([len(value) for value in dictionary.values()]) if dictionary else 0


def convert_dict_values_from_set_to_list(dictionary):
    """
    Return dictionary with key values as list, instead of set
    :param dictionary: {dict} with key values of type set.
    :return: {dict} dictionary with key values of type list.
    """
    return {k: list(v) for k, v in dictionary.items()}

from __future__ import annotations
import ipaddress
import re
from enum import Enum
from typing import List

from soar_sdk.SiemplifyUtils import convert_string_to_datetime, unix_now
from .constants import VALID_EMAIL_REGEXP
from .exceptions import McAfeeInvalidParamException


ENTITY_TYPES_MAPPING = {"MACADDRESS": "MacAddress"}


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


def is_different_items(items):
    """
    Is all items are same
    :param items: {iterable}
    """
    return len(set(items)) != 1


def filter_not_none_items(items):
    return list(filter(lambda item: item is not None, items))


def fix_status_for_duplicated_items(manager, success_entities, ignored_entities):
    """
    Filter and return only different entities by
    :param manager: {McafeeEpoManager} instance
    :param success_entities: {list} List of strings HOST or IP entity id
    :param ignored_entities: {list} List of strings HOST or IP entity id
    return {tuple} success_entities, ignored_entities
    """
    for system_info in filter_not_none_items(
        map(manager.get_system_info_safe, ignored_entities)
    ):
        if system_info.computer_name in success_entities:
            ignored_entities.remove(system_info.ip_address)
            success_entities.append(system_info.ip_address)
        elif system_info.ip_address in success_entities:
            ignored_entities.remove(system_info.computer_name)
            success_entities.append(system_info.computer_name)

    return success_entities, ignored_entities


def get_time_frame(start_time: str, end_time: str = None, validate=True) -> tuple:
    """
    Get Timeframe
    :param start_time: {str} The start of the timeframe
    :param end_time: {str} The end of the timeframe
    :param validate: {bool} raise if start > end
    :return: {tuple} Tuple as time frame (start_time (timestamp), end_time (timestamp))
    """
    formatted_start_time = format_time(start_time, "Start Time")
    formatted_end_time = (
        format_time(end_time, "End Time") if end_time else int(unix_now())
    )

    if validate:
        validate_time_range([formatted_start_time, formatted_end_time])

    return formatted_start_time, formatted_end_time


def format_time(time_to_format, time_name: str):
    """
    Convert time from string to timestamp
    :param time_to_format: {str} Time as string YYYY-MM-DDThh:mm:ssZ
    :param time_name: {str} Name of the time to format. Start Time / End Time
    :return: Time as timestamp. If the time is not time stamp and not of requested format, exception will be raised
    """
    try:
        return int(time_to_format)
    except ValueError:
        try:
            return int(convert_string_to_datetime(time_to_format).timestamp()) * 1000
        except Exception:
            raise McAfeeInvalidParamException(f"Invalid {time_name} was provided.")


def validate_time_range(time_range: List[int] = None) -> List[int]:
    """
    Validate time range
    :param time_range: {[int,int]} List of 2 unix timestamps in seconds. First value is start time, seconds value is end time
    :return: {[int,int]} Time range provided
        raise McAfeeInvalidParamException if failed to validate time range parameter
    """
    first, second = time_range

    if first < second:
        return time_range

    raise McAfeeInvalidParamException(
        f'Failed to validate "Start Time" and "End Time" parameters.'
    )


def get_existing_list(dictionary, key):
    if not dictionary.get(key):
        dictionary[key] = []

    return dictionary[key]


def is_valid_email(user_name):
    """
    Check if the user_name is valid email.
    :param user_name: {str} User name
    :return: {bool} True if valid email, else False
    """
    return bool(re.search(VALID_EMAIL_REGEXP, user_name))


def get_valid_emails(emails):
    return [email for email in emails if is_valid_email(email)]


def dotted_field_to_underscored(field):
    if field:
        return field.replace(".", "_")


def underscored_field_to_dotted(field):
    if field:
        return field.replace("_", ".")


def get_whitelist(siemplify):
    return (
        siemplify.whitelist
        if isinstance(siemplify.whitelist, list)
        else [siemplify.whitelist]
    )


def get_valid_v4_ip(ip):
    return int(ip) if str(ip).isnumeric() else ip


def ipv4_int(ip):
    ip = get_valid_v4_ip(ip)
    return ip if isinstance(ip, int) else ipv4_to(ip, int) if is_ipv4(ip) else ip


def ipv4_str(ip):
    ip = get_valid_v4_ip(ip)
    return ip if isinstance(ip, str) else ipv4_to(ip, str) if is_ipv4(ip) else ip


def is_ipv4(ip):
    return type(ipaddress.ip_address(ip)) is ipaddress.IPv4Address


def ipv4_to(value, _type):
    return _type(ipaddress.IPv4Address(value))


def ipv4_mapped_from_ipv6(ip):
    ipv6 = ipaddress.IPv6Address(ip)
    mapped = ipv6.ipv4_mapped
    if mapped:
        return str(mapped)


def get_entity_type(entity_type):
    return ENTITY_TYPES_MAPPING.get(entity_type, entity_type)


class SeverityLevelMappingEnum(Enum):
    CRITICAL = [0, 1, 2]
    HIGH = [3]
    MEDIUM = [4]
    LOW = [5]
    INFO = [6, 7]

    @classmethod
    def get_values(cls, level_name):
        found_level = cls.get_level_values_by_names(level_names=level_name)
        if found_level:
            return found_level

        raise Exception(f"Severity {level_name} not supported")

    @classmethod
    def get_level_values_by_names(cls, level_names, default=None):
        level_names = level_names if isinstance(level_names, list) else [level_names]
        return [
            value
            for level_name in map(str.lower, level_names)
            for level in cls
            if level_name == level.name.lower()
            for value in level.value
        ] or default

    @classmethod
    def get_level_name_by_value(cls, level_value):
        for level in cls:
            if level_value in level.value:
                return level.name

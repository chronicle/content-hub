from __future__ import annotations
import base64
import re
from soar_sdk.SiemplifyDataModel import EntityTypes
from .constants import EMAIL_REGEX, DOMAIN_REGEX, EMAIL_TYPE, DOMAIN_TYPE


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def encode_url(url):
    return base64.b64encode(url.encode()).rstrip(b"=").decode()


def prepare_entity_for_manager(entity):
    if entity.entity_type == EntityTypes.URL:
        return encode_url(get_entity_original_identifier(entity))

    return get_entity_original_identifier(entity)


def get_entity_type(entity):
    """
    Helper function for getting entity type
    :param entity: entity from which function will get type
    :return: {str} entity type
    """
    if (
        re.search(EMAIL_REGEX, get_entity_original_identifier(entity))
        and entity.entity_type == EntityTypes.USER
    ):
        return EMAIL_TYPE
    if (
        re.search(DOMAIN_REGEX, get_entity_original_identifier(entity))
        and entity.entity_type == EntityTypes.URL
    ):
        return DOMAIN_TYPE

    return entity.entity_type


def get_suitable_resources_ids(ids, exclude_prefixes=[]):
    """
    Exclude resources prefixed with unsupported UUID
    :param {iterable} resources ids
    :param {list} exclude_prefixes unsupported id prefixes
    :return: {list} suitable resources ids
    """
    suitable_ids = []
    for id in ids:
        exclude = False

        for exclude_prefix in exclude_prefixes:
            if id.startswith(exclude_prefix):
                exclude = True
                break

        if not exclude:
            suitable_ids.append(id)

    return suitable_ids


def remove_brackets(value):
    """
    Remove brackets from string
    :param value: {str}
    :return: {str} string without () characters
    """
    value = value.replace("(", "")
    return value.replace(")", "")


def replace_spaces_with_underscore(value):
    """
    Remove spaces from string
    :param value: {str}
    :return: {str} string with underscores instead of spaces
    """
    return value.replace(" ", "_")

from __future__ import annotations

import base64
import re

import tldextract
from soar_sdk.SiemplifyDataModel import EntityTypes

from .constants import DOMAIN_REGEX, DOMAIN_TYPE, EMAIL_REGEX, EMAIL_TYPE


def get_entity_original_identifier(entity):
    """Helper function for getting entity original identifier
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
    """Helper function for getting entity type
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


def get_domain_from_entity(identifier):
    """Extract domain from entity identifier
    :param identifier: {str} the identifier of the entity
    :return: {str} domain part from entity identifier
    """
    if "@" in identifier:
        return identifier.split("@", 1)[-1]
    try:
        result = tldextract.extract(identifier)
        if result.suffix:
            return ".".join([result.domain, result.suffix])
        return result.domain
    except ImportError:
        raise ImportError("tldextract is not installed. Use pip and install it.")

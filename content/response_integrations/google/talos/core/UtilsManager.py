from __future__ import annotations
import requests
from .TalosExceptions import TalosManagerError, TalosNotFoundManagerError


NOT_FOUND_ERROR = "Unfortunately, we can't find any results for your search."


def validate_response(response, error_msg="An error occurred"):
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise TalosManagerError(f"{error_msg}: {error} {response.content}")

    if "error" in response.json().keys():
        if response.json().get("error") == NOT_FOUND_ERROR:
            raise TalosNotFoundManagerError(NOT_FOUND_ERROR)

        raise TalosManagerError(response.json().get("error"))


def get_domain_from_entity(identifier):
    """
    Extract domain from entity identifier
    :param identifier: {str} the identifier of the entity
    :return: {str} domain part from entity identifier
    """
    if "@" in identifier:
        return identifier.split("@", 1)[-1]
    try:
        import tldextract

        result = tldextract.extract(identifier)
        join_with = "."
        if result.suffix:
            return join_with.join([result.domain, result.suffix])

        return result.domain

    except ImportError:
        raise ImportError("tldextract is not installed. Use pip and install it.")


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def convert_comma_separated_to_list(comma_separated):
    """
    Convert comma-separated string to list
    :param comma_separated: String with comma-separated values
    :return: List of values
    """
    return (
        [item.strip() for item in comma_separated.split(",")] if comma_separated else []
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

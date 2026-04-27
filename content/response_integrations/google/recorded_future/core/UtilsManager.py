from __future__ import annotations
from .exceptions import (
    RecordedFutureManagerError,
    RecordedFutureNotFoundError,
    RecordedFutureUnauthorizedError,
)
import requests


def validate_response(response):
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        if response.status_code == 404:
            raise RecordedFutureNotFoundError(error)

        if response.status_code == 401:
            raise RecordedFutureUnauthorizedError(error)

        try:
            response.json()
            error = response.json().get("error", []).get("message")
        except:
            pass

        raise RecordedFutureManagerError(error)


def check_errors_in_response(response):

    response.json()
    error = response.json().get("error")

    if len(error) != 0:
        error = error[0].get("reason")
        raise RecordedFutureManagerError(error)


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def get_recorded_future_id(entity):
    """
    Helper function for getting entity RF id
    :param entity: entity from which function will get RF id
    :return: {str} RF id if exists else empty
    """

    return entity.additional_properties.get("RF_id", "")


def get_recorded_future_document_id(entity):
    """
    Helper function for getting entity RF document id
    :param entity: entity from which function will get RF document id
    :return: {str} RF document id if exists else empty
    """

    return entity.additional_properties.get("RF_doc_id", "")

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

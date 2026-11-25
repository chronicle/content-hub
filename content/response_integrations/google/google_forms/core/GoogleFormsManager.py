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

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import requests
from google.auth.transport.requests import AuthorizedSession

from TIPCommon.base.interfaces import Apiable
from . import api_utils
from . import constants
from . import datamodels
from . import exceptions
from .GoogleFormsParser import GoogleFormsParser

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class GoogleFormsManager(Apiable):

    def __init__(
        self,
        session: AuthorizedSession,
        params: datamodels.IntegrationParameters,
    ) -> None:
        self.session = session
        self.parser = GoogleFormsParser()
        self.api_root = constants.API_ROOT
        self.logger = params.siemplify_logger

    def test_connectivity(self) -> None:
        """Test connectivity with Google Forms."""
        connectivity_err_msg = (
            f"Unable to test connectivity with {constants.INTEGRATION_NAME}"
        )

        request_url = api_utils.get_full_url(self.api_root, "list-users")
        response = self.session.get(
            request_url, params={"maxResults": 1, "customer": "my_customer"}
        )
        api_utils.validate_response(response, error_msg=connectivity_err_msg)

    def get_forms(
        self,
        form_id: str,
        max_alerts_to_fetch: int,
        max_hours_backwards: int,
        last_alert_time: datetime | None = None,
    ) -> list[datamodels.AlertResponse]:
        """Fetches forms and responses based on the provided filters.

        Args:
            form_id (str): The ID of the form to fetch responses for.
            max_alerts_to_fetch (int): Maximum number of alerts to fetch.
            max_hours_backwards (int): Maximum hours to look back for responses.
            last_alert_time (Optional[datetime]): The timestamp of the last alert
                processed.

        Returns:
            list[datamodels.AlertResponse]: A list of parsed alert responses.
        """
        time_range = self.create_response_time_filter(
            max_hours_backwards=max_hours_backwards, last_success_time=last_alert_time
        )

        params = {
            "filter": f"timestamp >= {time_range}",
            "pageSize": max_alerts_to_fetch,
        }

        url = api_utils.get_full_url(
            api_root=constants.CONNECTOR_API_ROOT,
            url_id="get_form",
            connector_api=True,
            form_Id=form_id,
        )
        response = self.session.get(url, params=params)

        return self.parser.build_alert_response(
            raw_data=response.json().get("responses", []),
            form_data=self.get_forms_detail(form_id=form_id),
        )

    def get_forms_detail(self, form_id: str) -> datamodels.form:
        """
        Retrieves form details by orchestrating request, parsing, and data model
        validation.

        Args:
            form_id (str): The ID of the form to retrieve details for.

        Returns:
            datamodels.form: An object containing the form's details.

        Raises:
            exceptions.GoogleFormsManagerError: Raised for network or general API
                errors.
            exceptions.InvalidJSONFormatException: Raised if JSON response is
                malformed.
            exceptions.GoogleFormsValidationException: Raised if the successfully
                parsed JSON data does not match the expected data model structure.
        """
        url = api_utils.get_full_url(
            constants.CONNECTOR_API_ROOT,
            url_id="get_form_details",
            connector_api=True,
            form_Id=form_id,
        )
        response_data = self._get_json_response_data(url, form_id)

        try:
            return self.parser.build_form(raw_data=response_data)
        except (KeyError, AttributeError, TypeError) as e:
            raise exceptions.GoogleFormsValidationException(
                f"Failed to validate data structure for form ID '{form_id}'. "
                f"Original error: {e}"
            ) from e

    def _get_json_response_data(self, url: str, form_id: str) -> SingleJson:
        """
        Executes an HTTP GET request, validates the response, and safely parses
        the JSON response.

        Args:
            url (str): The full API endpoint URL for the request.
            form_id (str): The ID of the form being requested, used for
                error messaging.

        Returns:
            SingleJson: The successfully parsed JSON response data,
                expected to contain the raw form details structure from the API.

        Raises:
            exceptions.GoogleFormsManagerError: Raised for network communication
                errors or general API errors (4xx/5xx status codes).
            exceptions.InvalidJSONFormatException: Raised if the API returns a
                successful status code (2xx) but the response body cannot be
                decoded as JSON.
        """
        try:
            response: requests.Response = self.session.get(url)
            error_msg: str = f"API error for form ID '{form_id}'"
            api_utils.validate_response(response, error_msg=error_msg)
            return response.json()

        except requests.exceptions.RequestException as e:
            raise exceptions.GoogleFormsManagerError(str(e)) from e

        except json.JSONDecodeError as e:
            raise exceptions.InvalidJSONFormatException(
                f"Failed to parse successful JSON response for form ID '{form_id}'."
            ) from e

    def create_response_time_filter(
        self,
        max_hours_backwards: int,
        last_success_time: int | None = None,
    ) -> str:
        """Create a time filter in ISO 8601 format based on the maximum hours backwards
            or the last success timestamp.

        Args:
            max_hours_backwards (int): Maximum time range in hours to look backwards.
            last_success_time (int, optional): Last success timestamp in milliseconds.
                Defaults to None.

        Returns:
            str: ISO 8601 formatted timestamp string.
        """
        if last_success_time:
            current_timestamp = int(datetime.now().timestamp())
            last_success_sec = last_success_time / constants.SEC_IN_MS
            hours_diff = (current_timestamp - last_success_sec) / constants.HOUR_IN_SEC
            time_value = hours_diff + 1
            filtered_datetime = datetime.now(tz=timezone.utc) - timedelta(
                hours=time_value
            )
        else:
            filtered_datetime = datetime.now(tz=timezone.utc) - timedelta(
                hours=max_hours_backwards
            )

        return filtered_datetime.replace(microsecond=0).isoformat() + "Z"

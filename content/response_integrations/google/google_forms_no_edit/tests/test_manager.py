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
import pytest
import requests

from google_forms.core import GoogleFormsManager
from google_forms.tests.common import MOCK_DATA


exceptions = GoogleFormsManager.exceptions

STATUS_CODES = {
    "SUCCESS": 200,
    "NOT_FOUND": 404,
    "BAD_REQUEST": 400,
    "CONFLICT": 409,
    "FORBIDDEN": 403,
    "INTERNAL_SERVER_ERROR": 500
}
FORM_ID = "abcdef"
INT_PARAM = 100
LOW = "Low"


def mock_request(
    mocker,
    session,
    request_string,
    method,
    status_code
):
    """Mocks a request for the given session, making it more realistic."""
    mock_response = mocker.Mock()
    mock_response.status_code = status_code
    mock_response.ok = status_code < 400

    json_payload = MOCK_DATA.get(request_string)
    mock_response.json.return_value = json_payload
    mock_response.text = json.dumps(json_payload) if json_payload else ""

    if not mock_response.ok:
        http_error = requests.exceptions.HTTPError(
            f"{status_code} Error",
            response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error

    mocker.patch.object(session, method, return_value=mock_response)


class TestGoogleFormsManager:
    """Unit tests for GoogleFormsManager"""

    def test_test_connectivity_valid_success(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """Test successful connectivity."""
        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="connectivity",
            method="get",
            status_code=STATUS_CODES["SUCCESS"],
        )
        mocker.patch("api_utils.validate_response")
        result = api_manager.test_connectivity()
        assert result is None

    def test_get_forms_detail_with_description(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """Test getting form details when the description field is present."""
        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="get_form_details",
            method="get",
            status_code=STATUS_CODES["SUCCESS"],
        )
        mocker.patch.object(
            api_manager.parser,
            "build_form",
            return_value=mocker.Mock(form_id=FORM_ID, description="Test Description")
        )
        result = api_manager.get_forms_detail(form_id=FORM_ID)

        assert result.form_id == FORM_ID
        assert result.description == "Test Description"

    def test_get_forms_detail_without_description(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """Test getting form details when the description field is missing."""
        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="get_form_details_no_description",
            method="get",
            status_code=STATUS_CODES["SUCCESS"],
        )
        mocker.patch.object(
            api_manager.parser,
            "build_form",
            return_value=mocker.Mock(form_id=FORM_ID, description="")
        )
        result = api_manager.get_forms_detail(form_id=FORM_ID)

        assert result.form_id == FORM_ID
        assert result.description == ""

    def test_get_forms(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """Test the get_forms method."""
        mock_form_details = mocker.Mock()
        mock_form_details.info.title = "Test Form"

        mocker.patch.object(
            api_manager,
            "get_forms_detail",
            return_value=mock_form_details,
        )

        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="get_forms",
            method="get",
            status_code=STATUS_CODES["SUCCESS"],
        )

        mocker.patch.object(
            api_manager.parser,
            "build_alert_response",
            return_value=[mocker.Mock()]
        )

        result = api_manager.get_forms(
            form_id=FORM_ID,
            max_alerts_to_fetch=INT_PARAM,
            max_hours_backwards=INT_PARAM,
        )

        assert len(result) > 0

    def test_get_forms_detail_api_error(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """Test that GoogleFormsManagerError is raised for API errors."""
        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="not_found_error",
            method="get",
            status_code=STATUS_CODES["NOT_FOUND"],
        )

        with pytest.raises(exceptions.GoogleFormsManagerError) as exc_info:
            api_manager.get_forms_detail(form_id=FORM_ID)

        error_str = str(exc_info.value)
        assert f"API error for form ID '{FORM_ID}'" in error_str
        assert "Requested entity was not found" in error_str

    def test_get_forms_detail_invalid_json(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """Test that InvalidJSONFormatException is raised for non-JSON responses."""
        mock_response = mocker.Mock()
        mock_response.status_code = STATUS_CODES["SUCCESS"]
        mock_response.ok = True
        mock_response.json.side_effect = json.JSONDecodeError(
            "Expecting value",
            "doc",
            0
        )
        mocker.patch.object(api_manager.session, "get", return_value=mock_response)

        with pytest.raises(exceptions.InvalidJSONFormatException) as exc_info:
            api_manager.get_forms_detail(form_id=FORM_ID)

        assert (
                   f"Failed to parse successful JSON response for form ID '{FORM_ID}'"
               ) in str(exc_info.value)

    def test_get_forms_detail_validation_error(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """Test that GoogleFormsValidationException is raised for data structure."""
        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="get_form_details_invalid_structure",
            method="get",
            status_code=STATUS_CODES["SUCCESS"],
        )

        mocker.patch.object(
            api_manager.parser,
            "build_form",
            side_effect=KeyError("Mocked KeyError: missing essential key")
        )

        with pytest.raises(exceptions.GoogleFormsValidationException) as exc_info:
            api_manager.get_forms_detail(form_id=FORM_ID)

        error_str = str(exc_info.value)
        assert (
                   f"Failed to validate data structure for form ID '{FORM_ID}'"
               ) in error_str
        assert "Mocked KeyError: missing essential key" in error_str

    def test_get_forms_detail_permission_denied(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """
        Test that GoogleFormsManagerError is raised with the correct
        message on a permission error (403 Forbidden).
        """
        error_payload = {
            "error": {
                "message": "The caller does not have permission"
            }
        }

        mock_response = mocker.Mock()
        mock_response.status_code = STATUS_CODES["FORBIDDEN"]

        mock_response.text = json.dumps(error_payload)
        mock_response.json.return_value = error_payload

        http_error = requests.exceptions.HTTPError(
            "403 Forbidden",
            response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error

        mocker.patch.object(api_manager.session, "get", return_value=mock_response)

        with pytest.raises(exceptions.GoogleFormsManagerError) as exc_info:
            api_manager.get_forms_detail(form_id=FORM_ID)

        error_str = str(exc_info.value)
        assert f"API error for form ID '{FORM_ID}'" in error_str
        assert "The caller does not have permission" in error_str


    def test_new_subclass_caught_by_base_class(
        self,
        mocker,
        api_manager: GoogleFormsManager.GoogleFormsManager,
    ) -> None:
        """
        Test that a newly created subclass (e.g., InvalidJSONFormatException)
        is correctly caught by its new base class (GoogleFormsManagerError).
        """
        mock_response = mocker.Mock()
        mock_response.status_code = STATUS_CODES["SUCCESS"]
        mock_response.ok = True

        mock_response.json.side_effect = json.JSONDecodeError(
            "Expecting value",
            "doc",
            0
        )
        mocker.patch.object(api_manager.session, "get", return_value=mock_response)

        with pytest.raises(exceptions.GoogleFormsManagerError) as exc_info:
            api_manager.get_forms_detail(form_id=FORM_ID)

        assert exc_info.type is exceptions.InvalidJSONFormatException
        assert isinstance(exc_info.value, exceptions.InvalidJSONFormatException)
        assert "Failed to parse successful JSON response" in str(exc_info.value)

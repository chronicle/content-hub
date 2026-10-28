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
import os
import pytest

import requests

from ..core import AuthenticationManager
from ..core import PaloAltoPrismaCloudManager


# Constants
with open(
    os.path.join(os.path.dirname(__file__), "mock_data.json"), encoding="UTF-8"
) as wf:
    MOCK_DATA = json.load(wf)

STATUS_CODES = {
    "SUCCESS": 200,
    "BAD_REQUEST": 400,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
}


def mock_request(
    mocker, session, request_string, method, status_code, raise_for_status=False
) -> None:
    """Mocks a request for the given session."""
    mock_response = mocker.Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = MOCK_DATA.get(request_string)

    if raise_for_status:
        mock_response.raise_for_status = requests.HTTPError("Unknown Error")

    mocker.patch.object(session, method, return_value=mock_response)


class TestPaloAltoPrismaCloudManager:
    """Unit tests for PaloAltoPrismaCloudManager"""

    def test_test_connectivity_valid_success(
        self,
        mocker,
        api_manager: PaloAltoPrismaCloudManager.ApiManager,
    ) -> None:
        """Test successful connectivity."""
        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="connectivity",
            method="post",
            status_code=STATUS_CODES["SUCCESS"],
        )
        result = api_manager.test_connectivity()

        assert result is None

    @pytest.mark.parametrize(
        "fallback_severity",
        ["Critical", "High", "Medium", "Low", "Informational"],
    )
    def test_get_alerts_valid_success(
        self,
        mocker,
        api_manager: PaloAltoPrismaCloudManager.ApiManager,
        fallback_severity: str,
    ) -> None:
        """Test getting alerts with valid severity."""
        mock_response = mocker.Mock()
        mock_response.json.return_value = MOCK_DATA.get("get_alerts")
        mock_response.status_code = STATUS_CODES["SUCCESS"]
        mocker.patch.object(api_manager.session, "request", return_value=mock_response)

        alert = api_manager.get_alerts(
            fallback_severity=fallback_severity,
            max_alerts_to_fetch=1,
            max_hours_backwards=10,
            last_alert_time=5,
        )

        assert type(alert[0]).__name__ == "AlertResponse"
        assert alert[0].__dict__["alert_id"] == "P-356"

    @pytest.mark.parametrize(
        "fallback_severity",
        ["invalid"],
    )
    def test_get_alerts_invalid_failed(
        self,
        mocker,
        api_manager: PaloAltoPrismaCloudManager.ApiManager,
        fallback_severity: str,
    ) -> None:
        """Test getting alerts with invalid severity."""
        mock_response = mocker.Mock()
        mock_response.json.return_value = MOCK_DATA.get("get_alerts")
        mock_response.status_code = STATUS_CODES["SUCCESS"]
        mocker.patch.object(api_manager.session, "request", return_value=mock_response)

        with pytest.raises(ValueError) as error:
            api_manager.get_alerts(
                fallback_severity=fallback_severity,
                max_alerts_to_fetch=1,
                max_hours_backwards=10,
                last_alert_time=5,
            )

        assert error.typename == "ValueError"
        assert 'Invalid "Lowest Severity To Fetch" level provided.' in str(error.value)

    def test_enrich_assets_valid_success(
        self, mocker, api_manager: PaloAltoPrismaCloudManager.ApiManager
    ) -> None:
        """Test successful asset enrichment."""
        asset_id = "b9634a8bbd5e0ed7cff079410270d147"

        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="enrich_assets",
            method="post",
            status_code=STATUS_CODES["SUCCESS"],
        )

        asset = api_manager.enrich_assets(asset=asset_id)

        assert asset.__dict__["id"] == asset_id
        assert type(asset).__name__ == "Asset"

    def test_verify_alert_valid_success(
        self, mocker, api_manager: PaloAltoPrismaCloudManager.ApiManager
    ) -> None:
        """Test successful alert verification."""
        alert_id = "I-226467"

        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="verify_alert",
            method="get",
            status_code=STATUS_CODES["SUCCESS"],
        )
        alert = api_manager.verify_alert(alert_id="I-226467", error_message=None)
        assert alert.__dict__["raw_data"]["id"] == alert_id
        assert type(alert).__name__ == "Alert"

    @pytest.mark.parametrize(
        "response_type", ["Dismiss", "Snooze", "Remediate", "Reopen"]
    )
    def test_build_alert_body_valid_success(
        self,
        response_type,
        api_manager: PaloAltoPrismaCloudManager.ApiManager,
    ) -> None:
        """Test building alert body with valid response types."""
        alert = api_manager.build_alert_body(
            alert_id="abcd",
            response_type=response_type,
            dismissal_note="test",
            snooze_time=10,
        )
        if response_type in ("Dismiss", "Snooze", "Reopen"):
            assert alert["alerts"] == ["abcd"]
        if response_type == "Dismiss":
            assert alert == MOCK_DATA.get("dismiss")
        if response_type == "Snooze":
            assert alert == MOCK_DATA.get("snooze")
        if response_type == "Reopen":
            assert alert == MOCK_DATA.get("reopen")

    @pytest.mark.parametrize(
        "response_type", ["Dismiss", "Snooze", "Remediate", "Reopen"]
    )
    def test_respond_to_alert_valid_success(
        self,
        mocker,
        response_type: str,
        api_manager: PaloAltoPrismaCloudManager.ApiManager,
    ) -> None:
        """Test responding to alert with valid response types."""
        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="verify_alert",
            method="get",
            status_code=STATUS_CODES["SUCCESS"],
        )
        response = api_manager.respond_to_alert(
            alert_id="abcd",
            response_type=response_type,
            dismissal_note="test",
            snooze_time=10,
            error_message=None,
        )

        expected_responses = {
            "Remediate": {"response_status": "Remediated"},
            "Dismiss": {"response_status": "Dismissed"},
            "Snooze": {"response_status": "Snoozed"},
            "Reopen": {"response_status": "Reopened"},
        }

        assert response == expected_responses.get(response_type)

    def test_generate_token_valid_success(
        self,
        mocker,
        auth_params: AuthenticationManager.SessionAuthenticationParameters,
        api_manager: PaloAltoPrismaCloudManager.ApiManager,
    ) -> None:
        """Test successful token generation."""
        auth_params.access_key_id = "abcd"
        auth_params.secret_access_key = "xxxxxx"
        mock_request(
            mocker=mocker,
            session=api_manager.session,
            request_string="token",
            method="post",
            status_code=STATUS_CODES["SUCCESS"],
        )

        token = AuthenticationManager.generate_token(
            session=api_manager.session, session_parameters=auth_params
        )

        assert token == MOCK_DATA.get("token")["token"]

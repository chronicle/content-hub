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

from unittest.mock import patch
import pytest

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon.transformation import dict_to_flat

from mandiant_digital_threat_monitoring.core.datamodels import Alert, Topic
from mandiant_digital_threat_monitoring.core.exceptions import MandiantDTMException
from mandiant_digital_threat_monitoring.core import (
    MandiantDTMManager,
    AuthenticationManager,
)


with open(
    os.path.join(os.path.dirname(__file__), "mock_data.json"), encoding="UTF-8"
) as wf:
    MOCK_DATA = json.load(wf)


class TestMandiantDTMManager:
    """Unit tests for MandiantDTMManager functions"""

    def test_test_connectivity_valid_success(
        self,
        mocker,
        api_manager: MandiantDTMManager.ApiManager,
    ) -> None:
        mock_data = MOCK_DATA.get("test_connectivity")
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data

        patch_object = patch.object(
            api_manager.session, "get", return_value=mock_get
        )

        with patch_object:
            result = api_manager.test_connectivity()
            assert result is None

    def test_test_connectivity_invalid_failed(
        self,
        api_manager: MandiantDTMManager.ApiManager,
    ) -> None:
        with patch.object(
            api_manager, "test_connectivity"
        ) as mock_test_connectivity:
            mock_test_connectivity.side_effect = MandiantDTMException()
            with pytest.raises(Exception) as error:
                api_manager.test_connectivity()

            assert error.typename == "MandiantDTMException"

    def test_get_alerts_valid_success(
        self,
        mocker,
        api_manager: MandiantDTMManager.ApiManager,
    ) -> None:
        mock_data = MOCK_DATA.get("get_alerts")
        mock_alert_data = mock_data.get("alerts")[0]
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data
        mock_get.headers = {"link": ""}

        patch_object = patch.object(
            api_manager.session, "get", return_value=mock_get
        )

        with patch_object:
            alerts = api_manager.get_alerts(
                "2024-06-24T10:51:23Z",
                limit=25,
                lowest_severity="Low",
                siemplify=mocker.Mock()
            )

            mock_alert = Alert(
                raw_data=mock_alert_data,
                raw_flat_data=dict_to_flat(mock_alert_data),
                alert_id=mock_alert_data.get("id"),
                status=mock_alert_data.get("status"),
                title=mock_alert_data.get("title"),
                created_at=convert_string_to_unix_time(
                    mock_alert_data.get("created_at")
                ),
                severity=mock_alert_data.get("severity"),
                alert_type=mock_alert_data.get("alert_type"),
                alert_summary=mock_alert_data.get("alert_summary"),
                aggregated_under_id=mock_alert_data.get("aggregated_under_id"),
                monitor_name=mock_alert_data.get("monitor_name"),
                topics=[
                    Topic(raw_data=topic) for topic in mock_alert_data.get("topics")
                ],
            )

            assert isinstance(alerts[0], Alert)
            assert mock_alert.alert_id == alerts[0].alert_id
            assert mock_alert.title == alerts[0].title
            assert mock_alert.created_at == alerts[0].created_at
            assert mock_alert.severity == alerts[0].severity
            assert mock_alert.alert_type == alerts[0].alert_type
            assert mock_alert.alert_summary == alerts[0].alert_summary
            assert mock_alert.aggregated_under_id == alerts[0].aggregated_under_id
            assert mock_alert.monitor_name == alerts[0].monitor_name
            assert mock_alert.topics == alerts[0].topics

    def test_get_alerts_invalid_failed(
        self,
        mocker,
        api_manager: MandiantDTMManager.ApiManager,
    ) -> None:
        with patch.object(api_manager, "get_alerts") as mock_get_alerts:
            mock_get_alerts.side_effect = MandiantDTMException()
            with pytest.raises(Exception) as error:
                api_manager.get_alerts(
                    "2024-06-24T10:51:23Z",
                    limit=25,
                    lowest_severity="Low",
                    siemplify=mocker.Mock(),
                )

            assert error.typename == "MandiantDTMException"

    def test_update_alert_success(self,mocker,
        api_manager: MandiantDTMManager.ApiManager,
    ) -> None:
        mock_data = MOCK_DATA.get("update_alert")
        mock_update_data = mock_data
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data

        patch_object = patch.object(
            api_manager.session, "patch", return_value=mock_get
        )

        with patch_object:
            response = api_manager.update_alert(
                "cpsl2xxxxxxxxxxxxxxx",
                "Read"
            )
            alerts = response.json()

            mock_alert = Alert(
                raw_data=mock_update_data,
                raw_flat_data=dict_to_flat(mock_update_data),
                alert_id=mock_update_data.get("id"),
                status=mock_update_data.get("status"),
                title=mock_update_data.get("title"),
                created_at=convert_string_to_unix_time(
                    mock_update_data.get("created_at")
                ),
                severity=mock_update_data.get("severity"),
                alert_type=mock_update_data.get("alert_type"),
                alert_summary=mock_update_data.get("alert_summary"),
                aggregated_under_id=mock_update_data.get("aggregated_under_id"),
                monitor_name=mock_update_data.get("monitor_name"),
                topics=[
                    Topic(raw_data=topic) for topic in mock_update_data.get("topics")
                ]
            )
            assert mock_alert.alert_id == alerts.get("id")
            assert mock_alert.status == alerts.get("status")

    def test_update_invalid_failed(self,
        api_manager: MandiantDTMManager.ApiManager,
    ) -> None:
        with patch.object(api_manager,"update_alert") as mock_update_alert:
            mock_update_alert.side_effect = MandiantDTMException()

            with pytest.raises(Exception) as error:
                api_manager.update_alert(
                    "cpsl2xxxxxxxxxxxxxxx",
                    "Resolved"
                )

            assert error.typename == "MandiantDTMException"




class TestAuthenticationManager:
    """Unit tests for AuthenticationManager functions"""
    def test_generate_access_token_valid_success(
        self,
        mocker,
        session,
        auth_params: AuthenticationManager.SessionAuthenticationParameters
    ) -> None:
        mock_data = MOCK_DATA.get("generate_access_token")
        mock_post = mocker.Mock()
        mock_post.json.return_value = mock_data

        patch_object = patch.object(
            session, "post", return_value=mock_post
        )

        with patch_object:
            result = AuthenticationManager.generate_access_token(
                session,
                auth_params
            )

            assert result == mock_data.get("access_token")

    def test_generate_access_token_invalid_failed(
        self,
        session,
        auth_params: AuthenticationManager.SessionAuthenticationParameters
    ) -> None:
        with patch.object(
            AuthenticationManager, "generate_access_token"
        ) as mock_generate_access_token:
            mock_generate_access_token.side_effect = MandiantDTMException()
            with pytest.raises(Exception) as error:
                AuthenticationManager.generate_access_token(
                    session,
                    auth_params
                )

            assert error.typename == "MandiantDTMException"

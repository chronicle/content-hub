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

from mandiant_managed_defense.core.datamodels import Alert, Event
from mandiant_managed_defense.core.exceptions import MandiantMDException
from mandiant_managed_defense.core import (
    MandiantMDManager,
    AuthenticationManager
)


with open(
    os.path.join(os.path.dirname(__file__), "mock_data.json"), encoding="UTF-8"
) as wf:
    MOCK_DATA = json.load(wf)


class TestMandiantMDManager:
    """Unit tests for MandiantMDManager functions"""
    def test_test_connectivity_valid_success(
        self,
        mocker,
        api_manager: MandiantMDManager.ApiManager,
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
        api_manager: MandiantMDManager.ApiManager,
    ) -> None:
        with patch.object(
            api_manager, "test_connectivity"
        ) as mock_test_connectivity:
            mock_test_connectivity.side_effect = MandiantMDException()
            with pytest.raises(Exception) as error:
                api_manager.test_connectivity()
            assert error.typename == "MandiantMDException"

    def test_get_investigations_valid_success(
        self,
        mocker,
        api_manager: MandiantMDManager.ApiManager,
    ) -> None:
        mock_data = MOCK_DATA.get("get_investigations")
        mock_alert_data = mock_data.get("data").get("objects")[0]
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data
        patch_object = patch.object(
            api_manager.session, "get", return_value=mock_get
        )
        with patch_object:
            alerts = api_manager.get_investigations(
                "2024-01-30T14:29:47Z",
                end_timestamp="2024-01-31T02:29:47Z",
                limit=10
            )
            mock_alert = Alert.from_json(raw_data=mock_alert_data)
            assert isinstance(alerts[0], Alert)
            assert mock_alert.alert_id == alerts[0].alert_id
            assert mock_alert.name == alerts[0].name
            assert mock_alert.description == alerts[0].description
            assert mock_alert.severity == alerts[0].severity
            assert mock_alert.alert_type == alerts[0].alert_type
            assert mock_alert.modified == alerts[0].modified
            assert mock_alert.external_id == alerts[0].external_id
            assert mock_alert.source_name == alerts[0].source_name

    def test_get_investigations_invalid_failed(
        self,
        api_manager: MandiantMDManager.ApiManager,
    ) -> None:
        with patch.object(
                api_manager,
                "get_investigations"
        ) as mock_get_investigations:
            mock_get_investigations.side_effect = MandiantMDException()
            with pytest.raises(Exception) as error:
                api_manager.get_investigations(
                    "2024-06-24T10:51:23Z",
                    end_timestamp="2024-06-24T22:51:23Z",
                    limit=10,
                )
            assert error.typename == "MandiantMDException"

    def test_get_investigations_details_valid_success(
        self,
        mocker,
        api_manager: MandiantMDManager.ApiManager,
    ) -> None:
        mock_data = MOCK_DATA.get("get_investigation_details")
        mock_event_data = mock_data.get("data").get("objects")[0]
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data
        patch_object = patch.object(
            api_manager.session, "get", return_value=mock_get
        )
        with patch_object:
            events = api_manager.get_investigation_details(
                external_id="1-4022611",
            )
            mock_event = Event.from_json(
                raw_data=mock_event_data,
            )
            assert isinstance(events[0], Event)
            assert mock_event.event_id == events[0].event_id
            assert mock_event.name == events[0].name
            assert mock_event.event_type == events[0].event_type
            assert mock_event.modified == events[0].modified
            assert mock_event.note_type == events[0].note_type

    def test_get_investigations_details_invalid_failed(
        self,
        api_manager: MandiantMDManager.ApiManager,
    ) -> None:
        with patch.object(
                api_manager,
                "get_investigation_details"
        ) as mock_get_investigation_details:
            mock_get_investigation_details.side_effect = MandiantMDException()
            with pytest.raises(Exception) as error:
                api_manager.get_investigation_details(
                    external_id="1-4022611",
                )
            assert error.typename == "MandiantMDException"


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
                auth_params
            )
            assert result == mock_data.get("access_token")

    def test_generate_access_token_invalid_failed(
        self,
        auth_params: AuthenticationManager.SessionAuthenticationParameters
    ) -> None:
        with patch.object(
            AuthenticationManager, "generate_access_token"
        ) as mock_generate_access_token:
            mock_generate_access_token.side_effect = MandiantMDException()
            with pytest.raises(Exception) as error:
                AuthenticationManager.generate_access_token(
                    auth_params
                )
            assert error.typename == "MandiantMDException"

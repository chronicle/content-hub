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

from unittest.mock import MagicMock, patch

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyDataModel import EntityTypes

from microsoft_teams.tests.test_actions.utils import (
    MockSiemplifyEntity,
    create_mock_response,
)
from microsoft_teams.actions.CreateChat import main

# pylint: disable=duplicate-code


def test_create_chat_success():
    """Test CreateChat action runs successfully."""
    user_email = "test@example.com"
    target_entity = MockSiemplifyEntity(
        identifier=user_email,
        entity_type=EntityTypes.USER
    )

    mock_siemplify = MagicMock()
    mock_siemplify.target_entities = [target_entity]

    mock_session_instance = MagicMock()
    mock_session_instance.headers = {}

    def mock_filter_users_api(*_args, **_kwargs):
        return create_mock_response(
            {
                "value": [
                    {
                        "id": "user-id-123",
                        "displayName": "test@example.com",
                        "mail": "test@example.com"
                    }
                ]
            }
        )

    def mock_check_account_api(url, **_kwargs):
        if "me" in url:
            return create_mock_response(
                {"id": "me-id-123", "userPrincipalName": "me@example.com"}
            )

        return create_mock_response({"value": [{"id": "dummy"}]})

    def mock_fetch_token_and_create_chat_api(url, **_kwargs):
        if "token" in url:
            return create_mock_response(
                {"access_token": "mock_token", "refresh_token": "mock"}
            )

        if "chats" in url:
            return create_mock_response({"id": "chat123"})

        return create_mock_response({})

    mock_session_instance.request.side_effect = mock_filter_users_api
    mock_session_instance.get.side_effect = mock_check_account_api
    mock_session_instance.post.side_effect = mock_fetch_token_and_create_chat_api

    def mock_extract_config(*args, **kwargs):
        param_name = kwargs.get("param_name")
        if not param_name and len(args) >= 3:
            param_name = args[2]

        if param_name == "Verify SSL":
            return False

        return "dummy"

    with patch(
        "microsoft_teams.actions.CreateChat"
        ".SiemplifyAction",
        return_value=mock_siemplify,
    ), patch(
        "microsoft_teams.actions.CreateChat"
        ".extract_configuration_param",
        side_effect=mock_extract_config,
    ), patch(
        "microsoft_teams.core.MicrosoftManager"
        ".requests.Session",
        return_value=mock_session_instance,
    ), patch(
        "requests.Session",
        return_value=mock_session_instance,
    ):
        main()

    mock_siemplify.end.assert_called_once()
    output_message, result_value, status = mock_siemplify.end.call_args[0]

    assert status == EXECUTION_STATE_COMPLETED
    assert result_value is True
    assert "Successfully created chat" in output_message

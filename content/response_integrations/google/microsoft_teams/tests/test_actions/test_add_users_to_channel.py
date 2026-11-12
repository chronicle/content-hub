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
from microsoft_teams.actions.AddUsersToChannel import main

# pylint: disable=duplicate-code


def test_add_users_to_channel_success():
    """Test AddUsersToChannel action runs successfully."""
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

    def mock_get_team_and_channel_api(url, **_kwargs):
        if "groups" in url:
            return create_mock_response(
                {"value": [{"id": "team-id-123", "displayName": "dummy"}]}
            )

        if "channels" in url:
            return create_mock_response(
                {
                    "value": [
                        {
                            "id": "channel-id-123",
                            "displayName": "dummy",
                            "membershipType": "private"
                        }
                    ]
                }
            )

        return create_mock_response({})

    def mock_fetch_token_and_add_user_api(url, **_kwargs):
        if "token" in url:
            return create_mock_response(
                {"access_token": "mock_token", "refresh_token": "mock"}
            )

        return create_mock_response({})

    mock_session_instance.request.side_effect = mock_filter_users_api
    mock_session_instance.get.side_effect = mock_get_team_and_channel_api
    mock_session_instance.post.side_effect = mock_fetch_token_and_add_user_api

    def mock_extract_config(*args, **kwargs):
        param_name = kwargs.get("param_name")
        if not param_name and len(args) >= 3:
            param_name = args[2]

        if param_name == "Verify SSL":
            return False

        return "dummy"

    with patch(
        "microsoft_teams.actions.AddUsersToChannel"
        ".SiemplifyAction",
        return_value=mock_siemplify,
    ), patch(
        "microsoft_teams.actions.AddUsersToChannel"
        ".extract_configuration_param",
        side_effect=mock_extract_config,
    ), patch(
        "microsoft_teams.actions.AddUsersToChannel"
        ".extract_action_param",
        return_value="dummy",
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
    assert "Successfully added the following users" in output_message

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
from unittest.mock import Mock, MagicMock
from urllib.parse import urljoin, quote

import pytest
import requests
from azure_active_directory.core import datamodels
from pytest_mock import MockerFixture

from requests.exceptions import HTTPError
from azure_active_directory.core.utils import is_valid_email
from azure_active_directory.core.exceptions import AzureADNotFoundError, AzureADError
from azure_active_directory.core.AzureADManager import AzureADManager
from azure_active_directory.tests.conftest import CONFIG


CUSTOM_LOGIN_ROOT: str = CONFIG["Login API Root"].rstrip("/") + "/"
CUSTOM_API_ROOT: str = CONFIG["API Root"].rstrip("/") + "/"
TENANT: str = CONFIG["Tenant"]

USER_IDENTIFIER: str = "user@example.com"
USER_ID: str = "user-guid-12345"
GROUP_ID: str = "group-guid-abcde"
DEVICE_NAME: str = "DESKTOP-TEST"


def test_generate_token_uses_custom_login_root(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Checks that generate_token builds the URL from the custom `login_api_root`.
    This test creates its own manager instance to test the real method logic.
    """
    mock_session: MagicMock = MagicMock()
    mock_session.headers = {}
    mock_session.post.return_value.json.return_value = {"access_token": "mock_token"}

    monkeypatch.setattr(requests, "Session", lambda: mock_session)

    AzureADManager(
        client_id=CONFIG["Client ID"],
        client_secret=CONFIG["Secret ID"],
        tenant=CONFIG["Tenant"],
        verify_ssl=CONFIG["Verify SSL"],
        api_root=CONFIG.get("API Root"),
        login_api_root=CONFIG.get("Login API Root"),
    )

    mock_session.post.assert_called_once()

    request_url: str = mock_session.post.call_args.args[0]
    expected_endpoint: str = f"{TENANT}/oauth2/v2.0/token"
    expected_url: str = urljoin(CUSTOM_LOGIN_ROOT, expected_endpoint)

    assert request_url == expected_url


def test_test_connectivity_builds_correct_url(
    azure_ad_manager: AzureADManager
) -> None:
    """Checks the URL for 'ping' (test_connectivity)."""
    azure_ad_manager.test_connectivity()

    azure_ad_manager.session.get.assert_called_once()
    request_url: str = azure_ad_manager.session.get.call_args.args[0]
    expected_url: str = urljoin(CUSTOM_API_ROOT, "v1.0")
    assert request_url == expected_url


def test_get_list_of_users_builds_correct_url(
    azure_ad_manager: AzureADManager,
    mocker: pytest.MockFixture
) -> None:
    """Checks the URL for 'users' (get_list_of_users)."""
    mocker.patch.object(azure_ad_manager, "_paginate_results", return_value=[])
    spy_paginate: Mock = mocker.spy(azure_ad_manager, "_paginate_results")
    azure_ad_manager.get_list_of_users(
        filter_field="All",
        filter_value="",
        filter_logic="Equal"
    )

    spy_paginate.assert_called_once()
    request_url: str = spy_paginate.call_args.kwargs["url"]
    expected_url: str = urljoin(CUSTOM_API_ROOT, "v1.0/users")
    assert request_url == expected_url


def test_user_methods_build_correct_url(
    azure_ad_manager: AzureADManager
) -> None:
    """Checks the URL for the 'user' endpoint used by several methods."""
    user_encoded = quote(USER_IDENTIFIER, safe="")
    expected_url: str = urljoin(CUSTOM_API_ROOT, f"v1.0/users/{user_encoded}")

    azure_ad_manager.get_user(user_principal_name=USER_IDENTIFIER)
    azure_ad_manager.session.get.assert_called_with(expected_url, params={})

    mock_response: MagicMock = MagicMock()
    mock_response.status_code = 204
    mock_response.raise_for_status.return_value = None
    azure_ad_manager.session.patch.return_value = mock_response

    azure_ad_manager.enable_user(user_principal_name=USER_IDENTIFIER)
    assert azure_ad_manager.session.patch.call_args.args[0] == expected_url

    azure_ad_manager.disable_user(user_principal_name=USER_IDENTIFIER)
    assert azure_ad_manager.session.patch.call_args.args[0] == expected_url


def test_add_user_to_group_builds_correct_url(
    azure_ad_manager: AzureADManager,
    mocker: pytest.MockFixture
) -> None:
    """Checks the URL for 'group_users' (add_user_to_group)."""
    mocker.patch.object(azure_ad_manager, "get_user_id", return_value=USER_ID)

    mock_response: MagicMock = MagicMock()
    mock_response.status_code = 204
    mock_response.raise_for_status.return_value = None
    azure_ad_manager.session.post.return_value = mock_response

    azure_ad_manager.add_user_to_group(
        group_id=GROUP_ID,
        user_principal_name=USER_IDENTIFIER
    )

    azure_ad_manager.session.post.assert_called_once()
    request_url: str = azure_ad_manager.session.post.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        f"v1.0/groups/{GROUP_ID}/members/$ref"
    )
    assert request_url == expected_url


def test_check_user_in_group_builds_correct_url(
    azure_ad_manager: AzureADManager
) -> None:
    """Checks the URL for 'user_member_of' (check_user_in_group)."""
    user_encoded = quote(USER_IDENTIFIER, safe="")
    azure_ad_manager.check_user_in_group(
        user_principal_name=USER_IDENTIFIER,
        group_id=GROUP_ID
    )

    azure_ad_manager.session.get.assert_called_once()
    request_url: str = azure_ad_manager.session.get.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        f"v1.0/users/{user_encoded}/memberOf"
    )
    assert request_url == expected_url


def test_get_users_manager_builds_correct_url(
    azure_ad_manager: AzureADManager
) -> None:
    """Checks the URL for 'manager' (get_users_manager)."""
    user_encoded = quote(USER_IDENTIFIER, safe="")
    azure_ad_manager.get_users_manager(user_principal_name=USER_IDENTIFIER)

    azure_ad_manager.session.get.assert_called_once()
    request_url: str = azure_ad_manager.session.get.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        f"v1.0/users/{user_encoded}/manager"
    )
    assert request_url == expected_url

    azure_ad_manager.session.get.reset_mock()
    azure_ad_manager.get_users_manager(
        user_principal_name=USER_IDENTIFIER,
        fields_to_return=["displayName", "sponsors"]
    )
    request_url = azure_ad_manager.session.get.call_args.args[0]
    expected_url_with_cast: str = urljoin(
        CUSTOM_API_ROOT,
        f"v1.0/users/{quote(USER_IDENTIFIER, safe='')}/manager/microsoft.graph.user"
    )
    assert request_url == expected_url_with_cast
    assert (
        azure_ad_manager.session.get.call_args.kwargs["params"]["$expand"] == "sponsors"
    )


def test_get_list_of_groups_builds_correct_url(
    azure_ad_manager: AzureADManager,
    mocker: pytest.MockFixture
) -> None:
    """Checks the URL for 'groups' (get_list_of_groups)."""
    mocker.patch.object(azure_ad_manager, "_paginate_results", return_value=[])
    spy_paginate: Mock = mocker.spy(azure_ad_manager, "_paginate_results")
    azure_ad_manager.get_list_of_groups(
        filter_value="",
        filter_logic="Equal",
        order_by="ASC"
    )

    spy_paginate.assert_called_once()
    request_url: str = spy_paginate.call_args.kwargs["url"]
    expected_url: str = urljoin(CUSTOM_API_ROOT, "v1.0/groups")
    assert request_url == expected_url


def test_get_host_builds_correct_url(
    azure_ad_manager: AzureADManager,
    mocker: pytest.MockFixture
) -> None:
    """Checks the URL for 'devices' (get_host)."""
    mocker.patch.object(
        azure_ad_manager.parser,
        "get_host_values",
        return_value=[MagicMock()]
    )

    azure_ad_manager.get_host(hostname=DEVICE_NAME)

    azure_ad_manager.session.get.assert_called_once()
    request_url: str = azure_ad_manager.session.get.call_args.args[0]
    expected_url: str = urljoin(CUSTOM_API_ROOT, "v1.0/devices")
    assert request_url == expected_url


def test_remove_user_from_group_builds_correct_url(
    azure_ad_manager: AzureADManager
) -> None:
    """Checks the URL for 'remove_user_from_group'."""
    mock_response: MagicMock = MagicMock()
    mock_response.status_code = 204
    mock_response.raise_for_status.return_value = None
    azure_ad_manager.session.delete.return_value = mock_response

    azure_ad_manager.remove_user_from_group(group_id=GROUP_ID, user_id=USER_ID)

    azure_ad_manager.session.delete.assert_called_once()
    request_url: str = azure_ad_manager.session.delete.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        f"v1.0/groups/{GROUP_ID}/members/{USER_ID}/$ref"
    )
    assert request_url == expected_url


def test_get_user_groups_builds_correct_url(
    azure_ad_manager: AzureADManager
) -> None:
    """Checks the URL for 'list_user_groups'."""
    user_encoded = quote(USER_IDENTIFIER, safe="")
    azure_ad_manager.get_user_groups(
        username=USER_IDENTIFIER,
        only_security_enabled_groups=True
    )

    azure_ad_manager.session.post.assert_called_once()
    request_url: str = azure_ad_manager.session.post.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        f"v1.0/users/{user_encoded}/getMemberGroups"
    )
    assert request_url == expected_url


def test_get_group_members_builds_correct_url(
    azure_ad_manager: AzureADManager,
    mocker: pytest.MockFixture
) -> None:
    """Checks the URL for 'group_members_details'."""
    mocker.patch.object(azure_ad_manager, "_paginate_results", return_value=[])
    spy_paginate: Mock = mocker.spy(azure_ad_manager, "_paginate_results")
    azure_ad_manager.get_group_members(
        filter_key="",
        filter_value="",
        filter_logic="Equal",
        group_id=GROUP_ID
    )

    spy_paginate.assert_called_once()
    request_url: str = spy_paginate.call_args.kwargs["url"]
    expected_url: str = urljoin(CUSTOM_API_ROOT, f"v1.0/groups/{GROUP_ID}/members")
    assert request_url == expected_url


def test_revoke_user_session_builds_correct_url(
    azure_ad_manager: AzureADManager
) -> None:
    """Checks the URL for 'revoke_user_session'."""
    azure_ad_manager.revoke_user_session(user_id=USER_ID)

    azure_ad_manager.session.post.assert_called_once()
    request_url: str = azure_ad_manager.session.post.call_args.args[0]
    expected_url: str = urljoin(
        CUSTOM_API_ROOT,
        f"v1.0/users/{USER_ID}/revokeSignInSessions"
    )
    assert request_url == expected_url


def test_get_group_by_name_success(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
):
    """
    Tests the successful search for a group by its name.
    """
    group_name = "Finance Department"
    mock_response_json = {
        "value": [
            {
                "id": "group-id-123",
                "displayName": group_name,
                "mailNickname": "finance"
            }
        ]
    }

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_json

    spy_get = mocker.patch.object(
        azure_ad_manager.session,
        "get",
        return_value=mock_response
    )

    result = azure_ad_manager.get_group_by_name(group_name)

    assert isinstance(result, datamodels.Group)
    assert result.id == "group-id-123"
    assert result.name == group_name

    spy_get.assert_called_once()

    call_args, call_kwargs = spy_get.call_args
    request_url = call_args[0]
    request_params = call_kwargs.get("params", {})

    expected_url = urljoin(CUSTOM_API_ROOT, "v1.0/groups")
    assert request_url == expected_url
    assert f"displayName eq '{group_name}'" in request_params["$filter"]
    assert f"mailNickname eq '{group_name}'" in request_params["$filter"]
    assert request_params["$select"] == "id,displayName,mailNickname"


def test_get_group_by_name_not_found(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
):
    """
    Tests the case where a group is not found by its name.
    """
    group_name = "NonExistent Group"
    mock_response_json = {"value": []}  # API returns an empty list

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_json

    mocker.patch.object(
        azure_ad_manager.session,
        "get",
        return_value=mock_response
    )

    result = azure_ad_manager.get_group_by_name(group_name)

    assert result is None


def test_get_group_by_name_handles_quotes(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
):
    """
    Tests that single quotes in the group name are correctly escaped.
    """
    group_name_with_quote = "IT O'Malley's Team"
    expected_sanitized_name = "IT O''Malley''s Team"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": []}

    spy_get = mocker.patch.object(
        azure_ad_manager.session,
        "get",
        return_value=mock_response
    )

    azure_ad_manager.get_group_by_name(group_name_with_quote)

    request_params = spy_get.call_args.kwargs.get("params", {})
    assert f"displayName eq '{expected_sanitized_name}'" in request_params["$filter"]


def test_get_user_id_with_filter_escapes_single_quotes(
    azure_ad_manager: AzureADManager
) -> None:
    """
    Tests that get_user_id_with_filter correctly escapes single quotes
    in user identifiers to prevent OData syntax errors.
    """
    user_identifier = "O'Malley"
    filter_keys = ["userPrincipalName", "mail"]
    expected_escaped_identifier = "O''Malley"

    azure_ad_manager.session.get.return_value.json.return_value = {"value": []}

    with pytest.raises(AzureADNotFoundError):
        azure_ad_manager.get_user_id_with_filter(user_identifier, filter_keys)

    call_args = azure_ad_manager.session.get.call_args
    assert call_args is not None
    params = call_args[1].get("params", {})
    filter_string = params.get("$filter", "")

    assert f"eq '{expected_escaped_identifier}'" in filter_string


def test_get_host_escapes_single_quotes(
    azure_ad_manager: AzureADManager
) -> None:
    """
    Tests that get_host correctly escapes single quotes in hostname
    to prevent OData syntax errors.
    """
    hostname = "Admin's-MacBook"
    expected_escaped_hostname = "Admin''s-MacBook"

    azure_ad_manager.session.get.return_value.json.return_value = {"value": []}

    with pytest.raises(AzureADError):
        azure_ad_manager.get_host(hostname)

    call_args = azure_ad_manager.session.get.call_args
    assert call_args is not None
    params = call_args[1].get("params", "")

    assert expected_escaped_hostname in params


def test_is_valid_email_allows_complex_identifiers():
    """
    Tests that the email validation utility correctly identifies complex identifiers
    used in Azure AD, including single quotes and #EXT# tags.
    """
    assert is_valid_email("o'malley@example.com") is True
    assert is_valid_email("DPELAEZ_ADAPTAS.COM#EXT#@NORGRENIT.ONMICROSOFT.COM") is True
    assert is_valid_email("test@example.com") is True
    assert is_valid_email("not-an-email") is False


def test_get_user_encodes_complex_url_paths(
    azure_ad_manager: AzureADManager
) -> None:
    """
    Checks that the manager correctly URL-encodes complex identifiers in the API path,
    specifically covering quotes and fragment symbols (#).
    """
    user_with_quote = "o'malley@example.com"
    expected_encoded_quote = quote(user_with_quote, safe="")
    azure_ad_manager.get_user(user_principal_name=user_with_quote)
    assert expected_encoded_quote in azure_ad_manager.session.get.call_args.args[0]

    external_user = "DPELAEZ_ADAPTAS.COM#EXT#@NORGRENIT.ONMICROSOFT.COM"
    expected_encoded_external = quote(external_user, safe="")

    azure_ad_manager.get_user(user_principal_name=external_user)
    assert expected_encoded_external in azure_ad_manager.session.get.call_args.args[0]


def test_get_user_registration_details_builds_correct_url(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
) -> None:
    """Checks the URL and params for 'user_registration_details'."""
    details = {
        "userPrincipalName": USER_IDENTIFIER,
        "isMfaRegistered": True,
        "methodsRegistered": ["mobilePhone"]
    }

    api_response = {"value": [details]}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = api_response
    mocker.patch.object(azure_ad_manager.session, "get", return_value=mock_response)

    result = azure_ad_manager.get_user_registration_details(USER_IDENTIFIER)

    azure_ad_manager.session.get.assert_called_once()
    call_args = azure_ad_manager.session.get.call_args

    request_url = call_args.args[0]
    request_params = call_args.kwargs["params"]

    url = "beta/reports/authenticationMethods/userRegistrationDetails"
    expected_url = urljoin(CUSTOM_API_ROOT, url)
    expected_filter = f"userPrincipalName eq '{USER_IDENTIFIER}'"

    assert request_url == expected_url
    assert request_params["$filter"] == expected_filter

    assert result["isMfaRegistered"] is True
    assert result["methodsRegistered"] == ["mobilePhone"]


def test_get_user_registration_details_with_apostrophe_in_upn(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
) -> None:
    """
    Checks that user registration details can be fetched for a UPN
    containing an apostrophe, and that the mock session correctly handles
    the escaped UPN in the filter.
    """
    user_with_apostrophe = "o'malley@example.com"
    expected_escaped_upn = "o''malley@example.com"

    details = {
        "userPrincipalName": user_with_apostrophe,
        "isMfaRegistered": True,
        "methodsRegistered": ["email"],
    }

    api_response = {"value": [details]}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = api_response
    mocker.patch.object(azure_ad_manager.session, "get", return_value=mock_response)

    result = azure_ad_manager.get_user_registration_details(user_with_apostrophe)

    azure_ad_manager.session.get.assert_called_once()
    call_args = azure_ad_manager.session.get.call_args

    request_url = call_args.args[0]
    request_params = call_args.kwargs["params"]

    url = "beta/reports/authenticationMethods/userRegistrationDetails"
    expected_url = urljoin(CUSTOM_API_ROOT, url)
    expected_filter_for_mock = f"userPrincipalName eq '{expected_escaped_upn}'"

    assert request_url == expected_url
    assert request_params["$filter"] == expected_filter_for_mock

    assert result["isMfaRegistered"] is True
    assert result["methodsRegistered"] == ["email"]


def test_get_user_registration_details_handles_403(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
) -> None:
    """Checks that 403 Forbidden returns empty dict gracefully."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {"error": {"message": "Access denied"}}

    error = HTTPError("403 Client Error")
    mock_response.raise_for_status.side_effect = error

    mocker.patch.object(azure_ad_manager.session, "get", return_value=mock_response)

    result = azure_ad_manager.get_user_registration_details(USER_IDENTIFIER)

    assert result == {}


def test_get_user_registration_details_raises_other_errors(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
) -> None:
    """Checks that other errors (e.g. 500) are re-raised."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": {"message": "Internal Server Error"}}

    error = HTTPError("500 Server Error")
    mock_response.raise_for_status.side_effect = error

    mocker.patch.object(azure_ad_manager.session, "get", return_value=mock_response)

    with pytest.raises(AzureADError):
        azure_ad_manager.get_user_registration_details(USER_IDENTIFIER)


def test_enrich_manager_with_mfa_success(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
) -> None:
    """
    Checks that enrich_manager_with_mfa successfully enriches manager with MFA details.
    """
    manager_upn: str = "manager@example.com"
    mfa_details: dict = {"isMfaRegistered": True}

    mock_supervisor: Mock = Mock()
    mock_supervisor.username = manager_upn
    mocker.patch.object(
        azure_ad_manager, "get_users_manager", return_value=mock_supervisor
    )
    mocker.patch.object(
        azure_ad_manager, "get_user_registration_details", return_value=mfa_details
    )

    user_manager: Mock = Mock()
    azure_ad_manager.enrich_manager_with_mfa(USER_IDENTIFIER, user_manager)

    azure_ad_manager.get_users_manager.assert_called_with(
        user_principal_name=USER_IDENTIFIER,
        fields_to_return=["userPrincipalName"]
    )
    azure_ad_manager.get_user_registration_details.assert_called_with(manager_upn)
    user_manager.set_mfa_details.assert_called_with(mfa_details)


def test_enrich_manager_with_mfa_missing_upn_logs_error(
    azure_ad_manager: AzureADManager,
    mocker: MockerFixture
) -> None:
    """
    Checks that enrich_manager_with_mfa logs error when manager UPN is missing.
    """
    mock_supervisor: Mock = Mock()
    mock_supervisor.username = None
    mocker.patch.object(
        azure_ad_manager, "get_users_manager", return_value=mock_supervisor
    )
    spy_get_details: Mock = mocker.patch.object(
        azure_ad_manager, "get_user_registration_details"
    )

    mock_logger: MagicMock = MagicMock()
    user_manager: Mock = Mock()

    azure_ad_manager.enrich_manager_with_mfa(
        USER_IDENTIFIER, user_manager, logger=mock_logger
    )

    azure_ad_manager.get_users_manager.assert_called_with(
        user_principal_name=USER_IDENTIFIER,
        fields_to_return=["userPrincipalName"]
    )
    spy_get_details.assert_not_called()
    user_manager.set_mfa_details.assert_not_called()
    mock_logger.error.assert_called_once()
    assert "userPrincipalName' is missing" in mock_logger.error.call_args[0][0]

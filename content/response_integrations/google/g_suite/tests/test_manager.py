from typing import Any, cast

import pytest
from TIPCommon.types import SingleJson

from g_suite.core.datamodels import (
    Browser,
    ExtensionDetails,
    OrgUnit,
    RequestingDevice,
    RequestingUser,
    ResolvedPolicy,
    UserActivityEvent,
)
from g_suite.core.exceptions import GSuiteNotFoundException
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.request import MockRequest


class TestUserOperations:
    def test_sign_out_valid(
        self,
        script_session: ApiSession,
        product: Product,
        gsuite_api_manager: GSuiteManager,
    ):
        username_ = "user@domain.com"
        product.add_user(username_)
        gsuite_api_manager.sign_out_user(username_)

        assert username_ in script_session.request_history[-1].request.url.geturl()
        assert script_session.request_history[-1].response.status_code == 200
        assert product.get_user(username_).is_logged_in is False

    def test_sign_out_invalid(
        self,
        script_session: ApiSession,
        gsuite_api_manager: GSuiteManager,
    ):
        # Use pytest.raises and check the exception type by its name. This is a robust
        # way to handle potential module import path issues.
        with pytest.raises(Exception) as excinfo:
            gsuite_api_manager.sign_out_user("invalid@domain.com")

        assert excinfo.type.__name__ == GSuiteNotFoundException.__name__

        assert (
            "invalid@domain.com"
            in script_session.request_history[-1].request.url.geturl()
        )
        assert script_session.request_history[-1].response.status_code == 404


class TestActivityOperations:
    def test_list_user_activity_events_valid(
        self,
        script_session: ApiSession,
        product: Product,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        user_key: str = "user@domain.com"
        app_name: str = "login"
        raw_mock_event: SingleJson = {
            "actor": {"email": user_key},
            "events": [
                {
                    "name": app_name,
                    "parameters": [{"name": "event", "value": "login_success"}],
                }
            ],
        }
        product.add_user_activity_events([UserActivityEvent(raw_mock_event)])

        events: list[UserActivityEvent] = gsuite_api_manager.list_user_activity_events(
            user_key=user_key,
            application_name=app_name,
            start_time="2023-01-01T00:00:00Z",
            end_time="2023-01-02T00:00:00Z",
            limit=10,
        )

        last_request_url: str = script_session.request_history[-1].request.url.geturl()
        assert f"users/{user_key}/applications/{app_name}" in last_request_url
        assert script_session.request_history[-1].response.status_code == 200
        assert len(events) == 1
        assert events[0].events[0]["parameters"][0]["value"] == "login_success"

    def test_list_user_activity_events_not_found(
        self,
        script_session: ApiSession,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        user_key: str = "nonexistent@domain.com"
        app_name: str = "login"

        events: list[UserActivityEvent] = gsuite_api_manager.list_user_activity_events(
            user_key=user_key,
            application_name=app_name,
            start_time="2023-01-01T00:00:00Z",
            end_time="2023-01-02T00:00:00Z",
            limit=10,
        )

        last_request_url: str = script_session.request_history[-1].request.url.geturl()
        assert f"users/{user_key}/applications/{app_name}" in last_request_url
        assert script_session.request_history[-1].response.status_code == 404
        assert not events


class TestBrowserOperations:
    def test_get_host_browser_details_valid(
        self,
        script_session: ApiSession,
        product: Product,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        hostname: str = "workstation-123"
        product.add_host_browser_details(
            [Browser({"browserId": "browser1", "machineName": hostname})]
        )

        browsers: list[Browser] = gsuite_api_manager.get_host_browser_details(hostname)

        last_request: MockRequest = script_session.request_history[-1].request
        assert f"machine_name:{hostname}" in last_request.kwargs["params"]["query"]
        assert script_session.request_history[-1].response.status_code == 200
        assert len(browsers) == 1
        assert browsers[0].browser_id == "browser1"

    def test_get_host_browser_details_not_found(
        self,
        script_session: ApiSession,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        hostname: str = "nonexistent-host"

        browsers: list[Browser] = gsuite_api_manager.get_host_browser_details(hostname)

        last_request: MockRequest = script_session.request_history[-1].request
        assert f"machine_name:{hostname}" in last_request.kwargs["params"]["query"]
        assert script_session.request_history[-1].response.status_code == 200
        assert not browsers


class TestExtensionOperations:
    def test_get_extension_details_valid(
        self,
        script_session: ApiSession,
        product: Product,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        ext_id: str = "abcdefghijklmnopabcdefghijklmnop"
        product.add_extension_details(
            [ExtensionDetails({"appId": ext_id, "displayName": "Test Extension"})]
        )

        details: ExtensionDetails = gsuite_api_manager.get_extension_details(ext_id)

        last_request_url: str = script_session.request_history[-1].request.url.geturl()
        assert f"apps/chrome/{ext_id}" in last_request_url
        assert script_session.request_history[-1].response.status_code == 200
        assert details.display_name == "Test Extension"

    def test_get_extension_details_invalid(
        self,
        script_session: ApiSession,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        ext_id: str = "invalidinvalidinvalidinvalidinva"

        with pytest.raises(Exception) as excinfo:
            gsuite_api_manager.get_extension_details(ext_id)

        assert excinfo.type.__name__ == GSuiteNotFoundException.__name__

        last_request_url: str = script_session.request_history[-1].request.url.geturl()
        assert f"apps/chrome/{ext_id}" in last_request_url
        assert script_session.request_history[-1].response.status_code == 404

    def test_get_extension_requesting_users_valid(
        self,
        script_session: ApiSession,
        product: Product,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        ext_id: str = "abcdefghijklmnopabcdefghijklmnop"
        product.add_requesting_users([RequestingUser({"email": "user@domain.com"})])

        users: list[RequestingUser] = gsuite_api_manager.get_extension_requesting_users(
            ext_id, 10
        )

        last_request_url: str = script_session.request_history[-1].request.url.geturl()
        assert "apps:fetchUsersRequestingExtension" in last_request_url
        assert script_session.request_history[-1].response.status_code == 200
        assert len(users) == 1
        assert users[0].user_email == "user@domain.com"

    def test_get_extension_requesting_devices_valid(
        self,
        script_session: ApiSession,
        product: Product,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        ext_id: str = "abcdefghijklmnopabcdefghijklmnop"
        product.add_requesting_devices([RequestingDevice({"deviceName": "device-123"})])

        devices: list[RequestingDevice] = (
            gsuite_api_manager.get_extension_requesting_devices(ext_id, 10)
        )

        last_request_url: str = script_session.request_history[-1].request.url.geturl()
        assert "apps:fetchDevicesRequestingExtension" in last_request_url
        assert script_session.request_history[-1].response.status_code == 200
        assert len(devices) == 1
        assert devices[0].device_name == "device-123"

    def test_block_extension_valid(
        self,
        script_session: ApiSession,
        product: Product,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        ext_id: str = "abcdefghijklmnopabcdefghijklmnop"
        ou_id: str = "ou_12345"
        product.add_org_units(
            [OrgUnit({"orgUnitId": f"id:{ou_id}", "name": "Test OU"})]
        )

        gsuite_api_manager.block_extension(ext_id, ou_id)

        last_history_item: Any = script_session.request_history[-1]
        assert "policies/orgunits:batchModify" in last_history_item.request.url.geturl()
        assert last_history_item.response.status_code == 200

        request_payload: dict[str, Any] = cast(
            dict[str, Any], last_history_item.request.kwargs.get("json", {})
        )
        assert (
            request_payload["requests"][0]["policyValue"]["value"]["appInstallType"]
            == "BLOCKED"
        )

    def test_resolve_policy_valid(
        self,
        script_session: ApiSession,
        product: Product,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        ext_id: str = "abcdefghijklmnopabcdefghijklmnop"
        ou_id: str = "ou_12345"
        product.add_resolved_policies(
            [ResolvedPolicy({"value": {"value": {"appInstallType": "BLOCKED"}}})]
        )

        policies: list[ResolvedPolicy] = gsuite_api_manager.resolve_policy(
            ext_id, ou_id
        )

        last_request_url: str = script_session.request_history[-1].request.url.geturl()
        assert "policies:resolve" in last_request_url
        assert script_session.request_history[-1].response.status_code == 200
        assert len(policies) == 1
        assert policies[0].install_type == "BLOCKED"

    def test_delete_extension_policy_valid(
        self,
        script_session: ApiSession,
        gsuite_api_manager: GSuiteManager,
    ) -> None:
        ext_id: str = "abcdefghijklmnopabcdefghijklmnop"
        ou_id: str = "ou_12345"

        gsuite_api_manager.delete_extension_policy(ext_id, ou_id)

        last_request_url: str = script_session.request_history[-1].request.url.geturl()
        assert "policies/orgunits:batchInherit" in last_request_url
        assert script_session.request_history[-1].response.status_code == 200

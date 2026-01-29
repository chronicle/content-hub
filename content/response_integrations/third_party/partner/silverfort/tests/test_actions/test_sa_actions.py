"""Tests for Service Account actions."""

from __future__ import annotations

from integration_testing.platform.script_output import (  # type: ignore[import-not-found]
    MockActionOutput,
)
from integration_testing.set_meta import set_metadata  # type: ignore[import-not-found]
from TIPCommon.base.action import ExecutionState  # type: ignore[import-not-found]

from silverfort.actions import get_service_account, list_service_accounts, update_sa_policy
from silverfort.tests.common import CONFIG_PATH
from silverfort.tests.core.product import MockSilverfort
from silverfort.tests.core.session import SilverfortSession


class TestGetServiceAccount:
    """Tests for the Get Service Account action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Service Account GUID": "82132169-b41b-8b47-ba4b-494814500785"},
    )
    def test_get_service_account_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful get service account."""
        get_service_account.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert "serviceAccounts" in request.url.path

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved service account" in action_output.results.output_message


class TestListServiceAccounts:
    """Tests for the List Service Accounts action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Page Size": "50", "Page Number": "1"},
    )
    def test_list_service_accounts_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful list service accounts."""
        list_service_accounts.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert "serviceAccounts/index" in request.url.path

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Page Size": "10", "Page Number": "1", "Fields": "guid,display_name,risk"},
    )
    def test_list_service_accounts_with_fields(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test list service accounts with specific fields."""
        list_service_accounts.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED


class TestUpdateSAPolicy:
    """Tests for the Update SA Policy action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Service Account GUID": "82132169-b41b-8b47-ba4b-494814500785",
            "Enabled": "true",
            "Block": "false",
        },
    )
    def test_update_sa_policy_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful update SA policy."""
        update_sa_policy.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert "serviceAccounts/policy" in request.url.path

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully updated" in action_output.results.output_message

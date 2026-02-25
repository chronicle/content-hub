"""Tests for Policy actions."""

from __future__ import annotations

from integration_testing.platform.script_output import (  # type: ignore[import-not-found]
    MockActionOutput,
)
from integration_testing.set_meta import set_metadata  # type: ignore[import-not-found]
from TIPCommon.base.action import ExecutionState  # type: ignore[import-not-found]

from silverfort.actions import change_policy_state, get_policy, list_policies, update_policy
from silverfort.tests.common import CONFIG_PATH
from silverfort.tests.core.product import MockSilverfort
from silverfort.tests.core.session import SilverfortSession


class TestGetPolicy:
    """Tests for the Get Policy action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Policy ID": "1"},
    )
    def test_get_policy_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful get policy."""
        get_policy.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert "policies" in request.url.path

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved policy" in action_output.results.output_message


class TestListPolicies:
    """Tests for the List Policies action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={},
    )
    def test_list_policies_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful list policies."""
        list_policies.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert "policies/index" in request.url.path

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved" in action_output.results.output_message


class TestUpdatePolicy:
    """Tests for the Update Policy action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Policy ID": "1", "Enabled": "true"},
    )
    def test_update_policy_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful update policy."""
        update_policy.main()

        assert len(script_session.request_history) >= 1

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully updated policy" in action_output.results.output_message


class TestChangePolicyState:
    """Tests for the Change Policy State action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Policy ID": "1", "Enable Policy": "true"},
    )
    def test_change_policy_state_enable(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful enable policy."""
        change_policy_state.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert "changePolicyState" in request.url.path

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "enabled" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Policy ID": "1", "Enable Policy": "false"},
    )
    def test_change_policy_state_disable(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful disable policy."""
        change_policy_state.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "disabled" in action_output.results.output_message

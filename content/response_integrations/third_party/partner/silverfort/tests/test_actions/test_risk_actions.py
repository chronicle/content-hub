"""Tests for Risk actions."""

from __future__ import annotations

from integration_testing.platform.script_output import (  # type: ignore[import-not-found]
    MockActionOutput,
)
from integration_testing.set_meta import set_metadata  # type: ignore[import-not-found]
from TIPCommon.base.action import ExecutionState  # type: ignore[import-not-found]

from silverfort.actions import get_entity_risk, update_entity_risk
from silverfort.tests.common import CONFIG_PATH
from silverfort.tests.core.product import MockSilverfort
from silverfort.tests.core.session import SilverfortSession


class TestGetEntityRisk:
    """Tests for the Get Entity Risk action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"User Principal Name": "test.user@example.com"},
    )
    def test_get_entity_risk_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful get entity risk."""
        get_entity_risk.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert "getEntityRisk" in request.url.path

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved risk" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"User Principal Name": "", "Resource Name": ""},
    )
    def test_get_entity_risk_no_identifier(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test get entity risk fails without identifier."""
        get_entity_risk.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "must be provided" in action_output.results.output_message


class TestUpdateEntityRisk:
    """Tests for the Update Entity Risk action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "User Principal Name": "test.user@example.com",
            "Risk Type": "activity_risk",
            "Severity": "high",
            "Valid For Hours": "24",
            "Description": "Test risk update",
        },
    )
    def test_update_entity_risk_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful update entity risk."""
        update_entity_risk.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert "updateEntityRisk" in request.url.path

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully updated risk" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "User Principal Name": "test.user@example.com",
            "Risk Type": "invalid_type",
            "Severity": "high",
            "Valid For Hours": "24",
            "Description": "Test risk update",
        },
    )
    def test_update_entity_risk_invalid_type(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test update entity risk fails with invalid risk type."""
        update_entity_risk.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Invalid risk type" in action_output.results.output_message

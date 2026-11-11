from __future__ import annotations

import pathlib

from soar_sdk.SiemplifyDataModel import DomainEntityInfo

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.smp_time import unix_now
from TIPCommon.types import SingleJson

from g_suite.actions.RevokeUserSessions import (
    RevokeUserSessions,
    SUCCESS_MESSAGE,
    NOT_FOUND_MESSAGE,
    NO_USERS_FOUND_MESSAGE,
)
from g_suite.core import consts

from g_suite.tests.common import CONFIG
from g_suite.tests.core.session import ApiSession
from g_suite.tests.core.product import Product
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR_MESSAGE = (
    f"Error executing action \"{consts.REVOKE_USER_SESSIONS_SCRIPT_NAME}\"\nReason: "
)
NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}No service account, workload identity "
    "email were provided, or missing mandatory fields for service account"
)
CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)

ACTION_CONFIG_WITH_VALID_INVALID = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_VALID_INVALID["User Email Addresses"] = (
    "invalid@domain.com,user@domain.com"
)

ACTION_CONFIG_WITH_INVALID = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_INVALID["User Email Addresses"] = "invalid@domain.com"


class TestAuth:

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS
    )
    def test_without_creds(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        RevokeUserSessions().run()

        assert len(script_session.request_history) >= 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )


class TestValid:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG,
    )
    def test_no_users(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        RevokeUserSessions().run()

        assert len(script_session.request_history) >= 1
        assert action_output.results.output_message == NO_USERS_FOUND_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is None

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_VALID_INVALID,
    )
    def test_valid_invalid_users(
            self,
            script_session: ApiSession,
            product: Product,
            action_output: MockActionOutput,
    ) -> None:
        username_ = "user@domain.com"
        product.add_user(username_)
        RevokeUserSessions().run()

        assert len(script_session.request_history) >= 3
        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(username_) +
            NOT_FOUND_MESSAGE.format("invalid@domain.com")
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is not None
        assert product.get_user(username_).is_logged_in is False

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_INVALID,
        entities=[
            DomainEntityInfo(
                identifier="user1@domain.com",
                additional_properties={"Environment": "Default Environment"},
                alert_identifier="test-alert",
                case_identifier=1,
                creation_time=unix_now(),
                modification_time=unix_now(),
                entity_type="UserUniqname",
                is_pivot=False,
                is_artifact=False,
                is_enriched=True,
                is_internal=True,
                is_suspicious=True,
                is_vulnerable=False,
            )
        ],
    )
    def test_valid_invalid_users_with_entity(
            self,
            script_session: ApiSession,
            product: Product,
            action_output: MockActionOutput,
    ) -> None:
        username_ = "user1@domain.com"
        product.add_user(username_)
        RevokeUserSessions().run()

        assert len(script_session.request_history) >= 4
        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(username_) +
            NOT_FOUND_MESSAGE.format("invalid@domain.com")
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is not None

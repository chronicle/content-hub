from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from ...actions import move_account_to_group
from ..common import CONFIG_PATH
from ..core.product import PortnoxCloud
from ..core.session import PortnoxCloudSession

ACCOUNT = "user@example.com"


class TestMoveAccountToGroup:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Group Name": "Quarantine", "Account ID": ""},
        entities=[create_entity(ACCOUNT, EntityTypesEnum.USER)],
    )
    def test_move_user_entity_to_existing_group_succeeds(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        portnox.accounts.add(ACCOUNT)
        portnox.groups.add("Quarantine")

        move_account_to_group.main()

        assert portnox.account_groups == {ACCOUNT: "Quarantine"}
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.output_message == (
            "Successfully moved accounts to group 'Quarantine' on the following entities using Portnox Cloud: "
            f"{ACCOUNT}"
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Group Name": "Missing Group", "Account ID": ACCOUNT},
    )
    def test_move_account_to_unknown_group_completes_unsuccessfully(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        portnox.accounts.add(ACCOUNT)

        move_account_to_group.main()

        assert not portnox.account_groups
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert action_output.results.output_message.startswith(
            "Action wasn't able to move accounts to group 'Missing Group' on the following entities using "
            f"Portnox Cloud: {ACCOUNT}"
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Group Name": "Quarantine", "Account ID": ""},
    )
    def test_move_without_targets_makes_no_api_call(
        self,
        script_session: PortnoxCloudSession,
        action_output: MockActionOutput,
    ) -> None:
        move_account_to_group.main()

        assert not script_session.request_history
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert action_output.results.output_message == (
            "No accounts to move. Provide the Account ID parameter or run the action on User entities."
        )

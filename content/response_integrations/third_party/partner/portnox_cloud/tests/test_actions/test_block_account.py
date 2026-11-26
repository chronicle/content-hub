from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from ...actions import block_account
from ..common import CONFIG_PATH
from ..core.product import PortnoxCloud
from ..core.session import PortnoxCloudSession

ACCOUNT = "user@example.com"
OTHER_ACCOUNT = "other@example.com"
UNKNOWN_ACCOUNT = "nobody@example.com"


def _add_accounts(portnox: PortnoxCloud) -> None:
    portnox.accounts.update({ACCOUNT, OTHER_ACCOUNT})


class TestBlockAccount:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Account ID": f'["{ACCOUNT}", "{OTHER_ACCOUNT}"]', "Reason": "Compromised account"},
    )
    def test_block_accounts_from_parameter_list_blocks_each_account(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_accounts(portnox)

        block_account.main()

        assert portnox.blocked_accounts == {ACCOUNT: "Compromised account", OTHER_ACCOUNT: "Compromised account"}
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.output_message == (
            f"Successfully blocked accounts on the following entities using Portnox Cloud: {ACCOUNT}, {OTHER_ACCOUNT}"
        )
        assert action_output.results.json_output.json_result == {
            "blocked": [ACCOUNT, OTHER_ACCOUNT],
            "failed": [],
            "reason": "Compromised account",
            "resolved_from": "Account ID parameter",
        }

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Account ID": "", "Reason": "Compromised account"},
        entities=[create_entity(ACCOUNT, EntityTypesEnum.USER)],
    )
    def test_block_account_without_parameter_uses_user_entities(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_accounts(portnox)

        block_account.main()

        assert portnox.blocked_accounts == {ACCOUNT: "Compromised account"}
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result["resolved_from"] == "User entities in the alert"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Account ID": f"{ACCOUNT}, {UNKNOWN_ACCOUNT}", "Reason": "Compromised account"},
    )
    def test_block_unknown_account_reports_it_and_blocks_the_rest(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_accounts(portnox)

        block_account.main()

        assert portnox.blocked_accounts == {ACCOUNT: "Compromised account"}
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.output_message == (
            f"Successfully blocked accounts on the following entities using Portnox Cloud: {ACCOUNT}\n"
            f"Action wasn't able to block accounts on the following entities using Portnox Cloud: {UNKNOWN_ACCOUNT}"
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Account ID": "", "Reason": "Compromised account"},
    )
    def test_block_account_without_targets_completes_unsuccessfully(
        self,
        script_session: PortnoxCloudSession,
        action_output: MockActionOutput,
    ) -> None:
        block_account.main()

        assert not script_session.request_history
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert action_output.results.output_message == (
            "No accounts to block. Provide the Account ID parameter or run the action on User entities."
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Account ID": ACCOUNT, "Reason": "Compromised account"},
    )
    def test_block_account_with_rejected_token_fails(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_accounts(portnox)

        with portnox.fail_requests(status_code=401):
            block_account.main()

        assert not portnox.blocked_accounts
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.output_message.startswith(
            'Error executing action "Block Account". Reason: Portnox Cloud rejected the credentials'
        )

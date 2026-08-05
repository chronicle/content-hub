from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from ellio.actions import AddIpToBlocklist
from ellio.tests.common import CONFIG_PATH
from ellio.tests.core.product import Ellio
from ellio.tests.core.session import EllioSession

PUBLIC_IP = "27.43.204.10"


class TestAddIpToBlocklist:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"IP Addresses": "", "Expires In Days": "14",
                    "Conflict Resolution": "extend"},
        entities=[create_entity(PUBLIC_IP, EntityTypesEnum.ADDRESS)],
    )
    def test_blocklist_add_success(
        self,
        script_session: EllioSession,
        action_output: MockActionOutput,
        ellio: Ellio,
    ) -> None:
        AddIpToBlocklist.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert PUBLIC_IP in action_output.results.output_message
        assert any(rule["ip"] == PUBLIC_IP for rule in ellio.blocklisted)

    @set_metadata(
        integration_config={
            "API Root": "https://api.ellio.tech",
            "API Key": "test-key",
            "Blocklist Ruleset ID": "",
            "Verify SSL": True,
        },
        parameters={"IP Addresses": "", "Expires In Days": "14",
                    "Conflict Resolution": "extend"},
        entities=[create_entity(PUBLIC_IP, EntityTypesEnum.ADDRESS)],
    )
    def test_blocklist_missing_ruleset_fails_upfront(
        self,
        script_session: EllioSession,
        action_output: MockActionOutput,
        ellio: Ellio,
    ) -> None:
        AddIpToBlocklist.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Blocklist Ruleset ID is not configured" in (
            action_output.results.output_message
        )

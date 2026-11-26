from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from ...actions import enrich_entities
from ..common import CONFIG_PATH
from ..core.product import PortnoxCloud

DEVICE_ID = "11111111-1111-4111-8111-111111111111"
MAC = "00:1C:42:AB:CD:EF"
UNKNOWN_MAC = "00:1C:42:00:00:99"
DEVICE = {
    "DeviceId": DEVICE_ID,
    "AllMacAddresses": [MAC],
    "AllIpAddresses": ["10.0.10.25"],
    "ComputerData": {"OsVersion": "Windows 11 Pro"},
    "RiskScore": 12,
}


class TestEnrichEntities:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Max Pages To Scan": 10, "Create Insight": True},
        entities=[create_entity(MAC, EntityTypesEnum.MAC_ADDRESS)],
    )
    def test_enrich_known_mac_returns_device_json(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        portnox.add_device("user@example.com", dict(DEVICE))

        enrich_entities.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.output_message == (
            f"Successfully enriched the following entities using Portnox Cloud: {MAC}"
        )
        json_result = action_output.results.json_output.json_result
        assert json_result[0]["Entity"] == MAC
        assert json_result[0]["EntityResult"]["DeviceId"] == DEVICE_ID
        assert json_result[0]["EntityResult"]["_Account"]["AccountName"] == "user@example.com"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Max Pages To Scan": 10, "Create Insight": False},
        entities=[create_entity(UNKNOWN_MAC, EntityTypesEnum.MAC_ADDRESS)],
    )
    def test_enrich_unknown_mac_completes_unsuccessfully(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        portnox.add_device("user@example.com", dict(DEVICE))

        enrich_entities.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert action_output.results.output_message == (
            f"Action wasn't able to enrich the following entities using Portnox Cloud: {UNKNOWN_MAC}"
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Max Pages To Scan": 10, "Create Insight": False},
        entities=[create_entity(MAC, EntityTypesEnum.MAC_ADDRESS)],
    )
    def test_enrich_with_rejected_token_fails(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        with portnox.fail_requests(status_code=401):
            enrich_entities.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.output_message.startswith(
            'Error executing action "Enrich Entities". Reason: Portnox Cloud rejected the credentials'
        )

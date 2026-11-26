from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from ...actions import block_device
from ..common import CONFIG_PATH
from ..core.product import PortnoxCloud
from ..core.session import PortnoxCloudSession

DEVICE_ID = "11111111-1111-4111-8111-111111111111"
SECOND_DEVICE_ID = "22222222-2222-4222-8222-222222222222"
MAC = "00:1C:42:AB:CD:EF"
SHARED_IP = "10.0.10.25"


def _add_devices(portnox: PortnoxCloud) -> None:
    portnox.add_device(
        "user@example.com",
        {"DeviceId": DEVICE_ID, "AllMacAddresses": [MAC], "AllIpAddresses": [SHARED_IP]},
    )
    portnox.add_device(
        "other@example.com",
        {"DeviceId": SECOND_DEVICE_ID, "AllMacAddresses": ["00:1C:42:00:00:02"], "AllIpAddresses": [SHARED_IP]},
    )


class TestBlockDevice:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Device ID": DEVICE_ID, "Reason": "Malware", "Max Pages To Scan": 10},
    )
    def test_block_device_by_device_id_blocks_that_device(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_devices(portnox)

        block_device.main()

        assert portnox.blocked_devices == {DEVICE_ID: "Malware"}
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.output_message == (
            f"Successfully blocked devices on the following entities using Portnox Cloud: {DEVICE_ID}"
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Device ID": "", "Reason": "Malware", "Max Pages To Scan": 10},
        entities=[create_entity(MAC, EntityTypesEnum.MAC_ADDRESS)],
    )
    def test_block_device_by_mac_entity_blocks_only_the_matching_device(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_devices(portnox)

        block_device.main()

        assert portnox.blocked_devices == {DEVICE_ID: "Malware"}
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Device ID": "", "Reason": "Malware", "Max Pages To Scan": 10},
        entities=[create_entity(SHARED_IP, EntityTypesEnum.ADDRESS)],
    )
    def test_block_device_by_ip_matching_two_devices_blocks_nothing(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_devices(portnox)

        block_device.main()

        assert not portnox.blocked_devices
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert action_output.results.output_message == (
            "More than one device matched the following entities, so none of them were blocked. "
            f"Use a MAC address or the Device ID parameter instead: {SHARED_IP}"
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Device ID": "", "Reason": "Malware", "Max Pages To Scan": 10},
        entities=[create_entity("10.0.10.2", EntityTypesEnum.ADDRESS)],
    )
    def test_block_device_by_ip_ignores_look_alike_addresses(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_devices(portnox)

        block_device.main()

        assert not portnox.blocked_devices
        assert action_output.results.result_value is False
        assert action_output.results.output_message == (
            "Action wasn't able to block devices on the following entities using Portnox Cloud: 10.0.10.2"
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Device ID": "", "Reason": "Malware", "Max Pages To Scan": -1},
    )
    def test_block_device_with_invalid_max_pages_fails(
        self,
        script_session: PortnoxCloudSession,
        action_output: MockActionOutput,
    ) -> None:
        block_device.main()

        assert not script_session.request_history
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.output_message == (
            'Error executing action "Block Device". Reason: Max Pages To Scan must be a positive number.'
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Device ID": DEVICE_ID, "Reason": "Malware", "Max Pages To Scan": 10},
    )
    def test_block_device_with_rejected_token_fails(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        _add_devices(portnox)

        with portnox.fail_requests(status_code=401):
            block_device.main()

        assert not portnox.blocked_devices
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.output_message.startswith(
            'Error executing action "Block Device". Reason: Portnox Cloud rejected the credentials'
        )

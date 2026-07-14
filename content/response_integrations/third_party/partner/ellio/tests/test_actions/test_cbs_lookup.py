from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from ellio.actions import CbsLookup
from ellio.tests.common import CONFIG_PATH
from ellio.tests.core.product import Ellio
from ellio.tests.core.session import EllioSession

CLOUD_IP = "13.107.42.14"
CBS_RECORD = {
    "ip": CLOUD_IP,
    "found": True,
    "cidr": "13.107.42.0/23",
    "labels": ["Cloud Providers > Microsoft Azure > Public Cloud"],
    "providers": ["azure"],
    "types": ["cloud"],
    "services": ["azurefrontdoor"],
    "regions": [],
}


class TestCbsLookup:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"IP Addresses": "", "Create Insight": True},
        entities=[create_entity(CLOUD_IP, EntityTypesEnum.ADDRESS)],
    )
    def test_cbs_match(
        self,
        script_session: EllioSession,
        action_output: MockActionOutput,
        ellio: Ellio,
    ) -> None:
        ellio.set_cbs(CLOUD_IP, CBS_RECORD)

        CbsLookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert CLOUD_IP in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"IP Addresses": "", "Create Insight": True},
        entities=[create_entity(CLOUD_IP, EntityTypesEnum.ADDRESS)],
    )
    def test_cbs_no_match(
        self,
        script_session: EllioSession,
        action_output: MockActionOutput,
        ellio: Ellio,
    ) -> None:
        CbsLookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False

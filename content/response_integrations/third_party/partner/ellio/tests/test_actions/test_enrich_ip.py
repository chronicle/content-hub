from __future__ import annotations

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from ellio.actions import EnrichIp
from ellio.tests.common import CONFIG_PATH
from ellio.tests.core.product import Ellio
from ellio.tests.core.session import EllioSession

MALICIOUS_IP = "27.43.204.10"
MALICIOUS_RECORD = {
    "seen": True,
    "classification": "malicious",
    "cve": ["CVE-2018-10561"],
    "tags": ["Exploit Attempt"],
    "network": {"ports": [443, 8080]},
    "first_seen": "2026-01-08",
    "last_seen": "2026-06-24",
}


class TestEnrichIp:
    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"IP Addresses": "", "Create Insight": True},
        entities=[create_entity(MALICIOUS_IP, EntityTypesEnum.ADDRESS)],
    )
    def test_enrich_malicious_recommends_high(
        self,
        script_session: EllioSession,
        action_output: MockActionOutput,
        ellio: Ellio,
    ) -> None:
        ellio.set_cti(MALICIOUS_IP, MALICIOUS_RECORD)

        EnrichIp.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value == "High"
        assert MALICIOUS_IP in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"IP Addresses": "", "Create Insight": True},
        entities=[create_entity(MALICIOUS_IP, EntityTypesEnum.ADDRESS)],
    )
    def test_enrich_not_in_ellio(
        self,
        script_session: EllioSession,
        action_output: MockActionOutput,
        ellio: Ellio,
    ) -> None:
        # no CTI record set - the API returns seen:false / 404
        EnrichIp.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value == "None"

from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

DNSRecordLookup = load_action("dns_record_lookup")


class TestDNSRecordLookup:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success_with_records(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dns_record_response({"results": [{"id": "r1", "name_in_zone": "host1", "type": "A"}]})

        DNSRecordLookup.main()

        assert any(r.request.url.path.endswith("/api/ddi/v1/dns/record") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 DNS record" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_records_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dns_record_response({"results": []})

        DNSRecordLookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "No DNS records found."

    @set_metadata(parameters={"Offset": "-1"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_offset_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        DNSRecordLookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            DNSRecordLookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False

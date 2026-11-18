from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"Detection ID": "34338"}


class TestDownloadPcap:
    def test_download_pcap_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Download PCAP")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "detection.pcap" in output.output_message
        assert len(siemplify.result.attachments) == 1
        assert siemplify.result.attachments[0]["filename"] == "detection.pcap"

    def test_download_pcap_not_found(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Download PCAP")
        product.download_pcap_status_code = 404
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_download_pcap_invalid_detection_id(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Download PCAP")
        output = run_action(action, siemplify, {"Detection ID": "not-a-number"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

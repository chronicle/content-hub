from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"Detection IDs": "101, 102"}


class TestOpenDetections:
    def test_open_detections_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Open Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert output.output_message == "The provided detection IDs have been successfully re-opened"

    def test_open_detections_invalid_ids(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Open Detections")
        output = run_action(action, siemplify, {"Detection IDs": "abc"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_open_detections_not_found(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("OPEN_DETECTIONS", 404, {"detail": "Not found."})
        action = load_action("Open Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Invalid Detection IDs" in output.output_message

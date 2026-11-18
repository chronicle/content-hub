from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"Entity ID": "68599", "Entity Type": "Host"}


class TestListEntityDetections:
    def test_list_entity_detections_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("List Entity Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved 1 detections for entity ID 68599" in output.output_message

    def test_list_entity_detections_no_detection_ids_on_entity(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        entity = product.describe_entity_response
        no_detections_entity = {
            "id": 68599,
            "name": "csoarqa-12",
            "type": "host",
            "severity": "Low",
            "urgency_score": 0,
            "last_detection_timestamp": "2024-11-27T20:39:32Z",
            "last_modified_timestamp": "2024-11-28T07:50:34Z",
            "attack_rating": 0,
            "state": "active",
            "tags": [],
            "url": "https://test.vectra.ai/api/v3.5/hosts/68599",
            "detection_set": [],
            "ip": "10.0.0.5",
        }
        product.describe_entity_response = [no_detections_entity]
        action = load_action("List Entity Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.output_message == "No detections found for entity ID 68599"

    def test_list_entity_detections_entity_not_found(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.describe_entity_response = []
        action = load_action("List Entity Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Entity not found" in output.output_message

    def test_list_entity_detections_invalid_limit(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("List Entity Detections")
        params = dict(DEFAULT_PARAMETERS)
        params["Limit"] = "0"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

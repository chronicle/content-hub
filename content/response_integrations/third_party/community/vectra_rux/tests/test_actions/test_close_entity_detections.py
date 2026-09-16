from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Entity ID": "68599", "Entity Type": "Host", "Reason": "Remediated"}


class TestCloseEntityDetections:
    def test_close_entity_detections_success(self, siemplify, mock_session, product):
        action = load_action("Close Entity Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "successfully closed as remediated" in output.output_message

    def test_close_entity_detections_no_detections(self, siemplify, mock_session, product):
        product.describe_entity_response = [
            {
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
        ]
        action = load_action("Close Entity Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.output_message == "No detections found for entity ID 68599"

    def test_close_entity_detections_invalid_entity_id(self, siemplify, mock_session, product):
        action = load_action("Close Entity Detections")
        params = dict(DEFAULT_PARAMETERS)
        params["Entity ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_close_entity_detections_entity_not_found(self, siemplify, mock_session, product):
        product.describe_entity_response = []
        action = load_action("Close Entity Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Entity not found" in output.output_message

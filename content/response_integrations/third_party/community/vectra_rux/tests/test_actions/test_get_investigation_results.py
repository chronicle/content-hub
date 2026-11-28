from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"Request ID": "req-123456"}


class TestGetInvestigationResults:
    def test_get_investigation_results_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Get Investigation Results")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Retrieved 1 investigation results for req-123456" in output.output_message

    def test_get_investigation_results_no_results(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.investigation_results_response = []
        action = load_action("Get Investigation Results")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert "No investigation results were found" in output.output_message

    def test_get_investigation_results_invalid_limit(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Get Investigation Results")
        params = dict(DEFAULT_PARAMETERS)
        params["Limit"] = "0"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_get_investigation_results_not_found(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("GET_INVESTIGATION_RESULTS", 404, {"detail": "Not found."})
        action = load_action("Get Investigation Results")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED


class TestGetInvestigationResultsPositionalFormat:
    COLUMNS = [
        ["timestamp", [{"type": "timestamp"}]],
        ["identity_principal", [{"type": "string"}]],
        ["operation", [{"type": "string"}]],
        [
            "extended_properties",
            [[{"name": {"type": "string"}, "value": {"type": "string"}}]],
        ],
        ["object_id", [{"type": "string"}]],
        [
            "device_properties",
            [[{"name": {"type": "string"}, "value": {"type": "string"}}]],
        ],
        ["client_ip", [{"type": "string"}]],
    ]

    def test_positional_rows_mapped_to_columns(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.investigation_results_meta = {"columns": self.COLUMNS}
        product.investigation_results_response = [
            [
                "2026-11-12T06:46:40+00:00",
                "serviceprincipal_1",
                "Update service principal.",
                [{"name": "category", "value": "ServicePrincipal"}],
                "obj-1",
                [],
                "",
            ],
        ]
        action = load_action("Get Investigation Results")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Retrieved 1 investigation results" in output.output_message


class TestRowsToDicts:
    COLUMNS = TestGetInvestigationResultsPositionalFormat.COLUMNS

    def test_positional_nested_struct_and_array(self) -> None:
        from UtilsManager import rows_to_dicts

        response = {
            "data": [["t", "p", "op", [["name1", "v1"]], "o", [], "ip"]],
            "meta": {"columns": self.COLUMNS},
        }
        assert rows_to_dicts(response, "data") == [
            {
                "timestamp": "t",
                "identity_principal": "p",
                "operation": "op",
                "extended_properties": [{"name": "name1", "value": "v1"}],
                "object_id": "o",
                "device_properties": [],
                "client_ip": "ip",
            },
        ]

    def test_keyed_nested_values_unchanged(self) -> None:
        from UtilsManager import rows_to_dicts

        nested = [{"name": "n", "value": "v"}]
        response = {
            "data": [["t", "p", "op", nested, "o", [], "ip"]],
            "meta": {"columns": self.COLUMNS},
        }
        assert rows_to_dicts(response, "data")[0]["extended_properties"] == nested

    def test_dict_rows_and_missing_meta_passthrough(self) -> None:
        from UtilsManager import rows_to_dicts

        rows = [{"a": 1}]
        assert rows_to_dicts({"data": rows}, "data") == rows
        assert rows_to_dicts({"data": rows, "meta": {"columns": self.COLUMNS}}, "data") == rows
        assert rows_to_dicts({}, "data") == []

    def test_old_columns_format_with_extra_entry(self) -> None:
        from UtilsManager import rows_to_dicts

        response = {
            "data": [["x"]],
            "meta": {"columns": [["timestamp", [{"type": "timestamp"}, ""]]]},
        }
        assert rows_to_dicts(response, "data") == [{"timestamp": "x"}]

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import json

from csv_integration.tests.common import CONFIG_PATH, get_mock_data
from csv_integration.tests.core.csv import CSV
from csv_integration.tests.test_save_json_to_csv.cases import (
    FILE_PATH,
    HAPPY_PATH_PARAMS,
    HAPPY_PATH_RESULTS,
    INVALID_JSON_PARAMS,
    INVALID_JSON_RESULTS,
    SINGLE_OBJECT_FILE_PATH,
    SINGLE_OBJECT_PARAMS,
    SINGLE_OBJECT_RESULTS,
    VERTICAL_UNPACK_FILE_PATH,
    VERTICAL_UNPACK_PARAMS,
    VERTICAL_UNPACK_RESULTS,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from csv_integration.actions import SaveJsonToCSV as SaveJsonToCsvScript


class TestHappyPath:
    """Tests for successful execution of SaveJsonToCSV."""

    @set_metadata(
        parameters=HAPPY_PATH_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_list_of_objects_happy_path(
        self,
        mock_csv_product: CSV,
        action_output: MockActionOutput,
    ) -> None:
        """Tests saving a list of JSON objects to CSV (wide format)."""
        SaveJsonToCsvScript.main()

        expected_content: str = get_mock_data("expected_simple_csv")
        written_content: str | None = mock_csv_product.get_written_content(
            FILE_PATH
        )

        assert written_content is not None
        assert written_content.strip() == expected_content.strip()
        assert action_output.results == HAPPY_PATH_RESULTS

    @set_metadata(
        parameters=SINGLE_OBJECT_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_single_object_happy_path(
        self,
        mock_csv_product: CSV,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that a single JSON object is converted correctly (wide format)."""
        SaveJsonToCsvScript.main()

        expected_content: str = get_mock_data("expected_single_object_csv")
        written_content: str | None = mock_csv_product.get_written_content(
            SINGLE_OBJECT_FILE_PATH
        )

        assert written_content is not None
        assert written_content.strip() == expected_content.strip()
        assert action_output.results == SINGLE_OBJECT_RESULTS

    @set_metadata(
        parameters=VERTICAL_UNPACK_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_vertical_unpacking_happy_path(
        self,
        mock_csv_product: CSV,
        action_output: MockActionOutput,
    ) -> None:
        """Tests saving a complex nested JSON with Vertical Unpacking."""
        SaveJsonToCsvScript.main()

        expected_content: str = get_mock_data("expected_vertical_csv")
        written_content: str | None = mock_csv_product.get_written_content(
            VERTICAL_UNPACK_FILE_PATH
        )

        assert written_content is not None
        assert written_content.strip() == expected_content.strip()
        assert action_output.results == VERTICAL_UNPACK_RESULTS


class TestErrorPath:
    """Tests for expected failures of SaveJsonToCSV."""

    @set_metadata(
        parameters=INVALID_JSON_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_invalid_json_is_handled_gracefully(
        self,
        action_output: MockActionOutput,
    ) -> None:
        """Tests that the script fails when provided with malformed JSON."""
        SaveJsonToCsvScript.main()

        assert (
            "The JSON structure is invalid"
            in action_output.results.output_message
        )
        assert (
            action_output.results.execution_state
            == INVALID_JSON_RESULTS.execution_state
        )
        assert (
            action_output.results.result_value
            == INVALID_JSON_RESULTS.result_value
        )


class TestStressPath:
    """Stress tests for the 'Advanced Nested JSON Handling' feature."""

    @set_metadata(
        parameters={
            "File Path": "/tmp/vertical_unpack_below_limit.csv",
            "JSON Object": json.dumps(
                {
                    "a": [1, 2, 3, 4],
                    "b": [1, 2, 3, 4],
                    "c": [1, 2, 3, 4],
                    "d": [1, 2, 3, 4],
                    "e": [1, 2, 3, 4],
                }
            ),  # 4**5 = 1024 rows
            "Advanced Nested JSON Handling": True,
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_vertical_unpack_cartesian_product_below_limit(
        self,
        mock_csv_product: CSV,
        action_output: MockActionOutput,
    ) -> None:
        """
        Tests that vertical unpacking with a Cartesian product smaller than
        the max_rows limit is NOT truncated.
        """
        SaveJsonToCsvScript.main()

        written_content: str | None = mock_csv_product.get_written_content(
            "/tmp/vertical_unpack_below_limit.csv"
        )

        assert action_output.results.result_value is True
        assert written_content is not None
        # Header + 1024 data rows = 1025 lines
        assert len(written_content.strip().split("\n")) == 1025

    @set_metadata(
        parameters={
            "File Path": "/tmp/vertical_unpack_large_list.csv",
            "JSON Object": json.dumps(
                [{"id": i} for i in range(50000)]
            ),
            "Advanced Nested JSON Handling": True,
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_vertical_unpack_large_list(
        self,
        mock_csv_product: CSV,
        action_output: MockActionOutput,
    ) -> None:
        """
        Tests that the new logic path correctly handles a large list of
        simple objects without Cartesian explosion.
        """
        SaveJsonToCsvScript.main()

        written_content: str | None = mock_csv_product.get_written_content(
            "/tmp/vertical_unpack_large_list.csv"
        )

        assert action_output.results.result_value is True
        assert written_content is not None
        # Header + 50,000 data rows = 50,001 lines
        assert len(written_content.strip().split("\n")) == 50001

    @set_metadata(
        parameters={
            "File Path": "/tmp/json_bomb_test.csv",
            "JSON Object": json.dumps(
                {f"k{i}": [1, 2, 3] for i in range(30)}
            ),
            "Advanced Nested JSON Handling": True,
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_vertical_unpack_json_bomb_hits_limit(
        self,
        mock_csv_product: CSV,
        action_output: MockActionOutput,
    ) -> None:
        """
        Tests that the 'max_rows' safeguard correctly truncates the output
        when a 'JSON Bomb' (large Cartesian product) is provided.
        """
        SaveJsonToCsvScript.main()

        written_content: str | None = mock_csv_product.get_written_content(
            "/tmp/json_bomb_test.csv"
        )

        assert action_output.results.result_value is True
        assert written_content is not None
        # Header + 500,000 data rows (the limit) = 500,001 lines
        assert len(written_content.strip().split("\n")) == 500001

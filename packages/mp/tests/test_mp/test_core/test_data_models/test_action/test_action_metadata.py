# Copyright 2025 Google LLC
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
from pathlib import Path

from hypothesis import given, settings

from mp.core.data_models.integrations.action.metadata import (
    ActionMetadata,
    BuiltActionMetadata,
    NonBuiltActionMetadata,
    _load_json_examples,  # noqa: PLC2701
)
from test_mp.test_core.test_data_models.utils import FILE_NAME

from .strategies import (
    ST_VALID_BUILT_ACTION_METADATA_DICT,
    ST_VALID_NON_BUILT_ACTION_METADATA_DICT,
)


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=ST_VALID_NON_BUILT_ACTION_METADATA_DICT)
    def test_valid_non_built(self, valid_non_built: NonBuiltActionMetadata) -> None:
        ActionMetadata.from_non_built(FILE_NAME, valid_non_built)

    @settings(max_examples=30)
    @given(valid_built=ST_VALID_BUILT_ACTION_METADATA_DICT)
    def test_valid_built(self, valid_built: BuiltActionMetadata) -> None:
        ActionMetadata.from_built(FILE_NAME, valid_built)


class TestLoadJsonExamples:
    """Tests for _load_json_examples preserving all DRM entries."""

    def test_null_result_example_path_is_preserved(self) -> None:
        """DRM with result_example_path=None must be kept with show_result intact."""
        drms = [{"result_example_path": None, "result_name": "JsonResult", "show_result": True}]
        result = _load_json_examples(drms, Path("/unused"))
        assert len(result) == 1
        assert result[0]["result_example_path"] == "{}"
        assert result[0]["result_name"] == "JsonResult"
        assert result[0]["show_result"] is True

    def test_empty_string_result_example_path_is_preserved(self) -> None:
        """DRM with result_example_path='' must be kept with show_result intact."""
        drms = [{"result_example_path": "", "result_name": "JsonResult", "show_result": True}]
        result = _load_json_examples(drms, Path("/unused"))
        assert len(result) == 1
        assert result[0]["result_example_path"] == "{}"
        assert result[0]["show_result"] is True

    def test_valid_result_example_path_loads_json(self, tmp_path: Path) -> None:
        """DRM with a valid path must load the JSON content from the file."""
        json_content = {"key": "value"}
        json_file = tmp_path / "resources" / "example.json"
        json_file.parent.mkdir(parents=True)
        json_file.write_text(json.dumps(json_content), encoding="utf-8")

        drms = [{"result_example_path": "resources/example.json", "result_name": "JsonResult", "show_result": True}]
        result = _load_json_examples(drms, tmp_path / "actions")
        assert len(result) == 1
        assert json.loads(result[0]["result_example_path"]) == json_content

    def test_mixed_null_and_valid_paths_all_preserved(self, tmp_path: Path) -> None:
        """All DRM entries must be preserved regardless of whether path is null or valid."""
        json_content = {"data": [1, 2, 3]}
        json_file = tmp_path / "resources" / "action_JsonResult_example.json"
        json_file.parent.mkdir(parents=True)
        json_file.write_text(json.dumps(json_content), encoding="utf-8")

        drms = [
            {"result_example_path": None, "result_name": "JsonResult", "show_result": True},
            {
                "result_example_path": "resources/action_JsonResult_example.json",
                "result_name": "JsonResult",
                "show_result": False,
            },
            {"result_example_path": "", "result_name": "OtherResult", "show_result": True},
        ]
        result = _load_json_examples(drms, tmp_path / "actions")
        assert len(result) == 3
        assert result[0]["result_example_path"] == "{}"
        assert result[0]["show_result"] is True
        assert json.loads(result[1]["result_example_path"]) == json_content
        assert result[1]["show_result"] is False
        assert result[2]["result_example_path"] == "{}"
        assert result[2]["show_result"] is True

    def test_does_not_mutate_input(self) -> None:
        """Input DRM dicts must not be modified in place."""
        drms = [{"result_example_path": None, "result_name": "JsonResult", "show_result": True}]
        _load_json_examples(drms, Path("/unused"))
        assert drms[0]["result_example_path"] is None

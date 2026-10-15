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

from typing import Any

from csv_integration.core.utils import flatten_json_vertically


class TestFlattenJson:
    def test_flatten_simple_dict(self) -> None:
        data: dict[str, Any] = {"a": 1, "b": "test"}
        assert flatten_json_vertically(data) == [{"a": "1", "b": "test"}]

    def test_flatten_nested_dict(self) -> None:
        data: dict[str, Any] = {"a": 1, "b": {"c": 2, "d": "nested"}}
        expected: list[dict[str, str]] = [{"a": "1", "b_c": "2", "b_d": "nested"}]
        assert flatten_json_vertically(data, sep="_") == expected

    def test_flatten_list_of_scalars(self) -> None:
        data: dict[str, list[int]] = {"a": [1, 2, 3]}
        expected: list[dict[str, str]] = [{"a": "1"}, {"a": "2"}, {"a": "3"}]
        assert flatten_json_vertically(data) == expected

    def test_flatten_list_of_dicts(self) -> None:
        data: dict[str, list[dict[str, Any]]] = {
            "items": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        }
        expected: list[dict[str, str]] = [{"items_id": "1", "items_name": "A"},
                                          {"items_id": "2", "items_name": "B"}]
        assert flatten_json_vertically(data, sep="_") == expected

    def test_flatten_with_empty_list(self) -> None:
        data: dict[str, Any] = {"a": 1, "b": []}
        assert flatten_json_vertically(data) == [{"a": "1"}]

    def test_flatten_with_none_values(self) -> None:
        data: dict[str, Any] = {"a": 1, "b": None, "c": {"d": None}}
        expected: list[dict[str, str]] = [{"a": "1", "b": "", "c_d": ""}]
        assert flatten_json_vertically(data, sep="_") == expected

    def test_flatten_empty_dict(self) -> None:
        assert not flatten_json_vertically({})

    def test_flatten_empty_list_top_level(self) -> None:
        assert not flatten_json_vertically([])

    def test_cartesian_product(self) -> None:
        data: dict[str, Any] = {
            "id": "p1",
            "colors": ["red", "blue"],
            "sizes": ["S", "M"],
        }
        expected: list[dict[str, str]] = [
            {"id": "p1", "colors": "red", "sizes": "S"},
            {"id": "p1", "colors": "red", "sizes": "M"},
            {"id": "p1", "colors": "blue", "sizes": "S"},
            {"id": "p1", "colors": "blue", "sizes": "M"},
        ]
        # Sort the keys of each dict to ensure comparison is order-independent
        result: list[dict[str, str]] = [dict(sorted(d.items())) for d in
                                        flatten_json_vertically(data)]
        expected_sorted: list[dict[str, str]] = [dict(sorted(d.items())) for d in
                                                 expected]
        assert result == expected_sorted

    def test_deeply_nested_structure(self) -> None:
        data: dict[str, Any] = {
            "a": {
                "b": {
                    "c": 1,
                },
                "d": [
                    {"e": 2},
                    {"f": 3},
                ],
            },
        }
        expected: list[dict[str, str]] = [
            {"a_b_c": "1", "a_d_e": "2"},
            {"a_b_c": "1", "a_d_f": "3"},
        ]
        result: list[dict[str, str]] = [dict(sorted(d.items())) for d in
                                        flatten_json_vertically(data, sep="_")]
        expected_sorted: list[dict[str, str]] = [dict(sorted(d.items())) for d in
                                                 expected]
        assert result == expected_sorted

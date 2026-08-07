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

import pathlib
from unittest.mock import MagicMock
from ..core.ProofPointTapParser import build_results


def test_build_results_success():
    """Verify that the method is called directly with item and kwargs."""
    mock_method = MagicMock(side_effect=lambda x, **kwargs: f"processed_{x}")
    raw_json = {"data": [1, 2, 3]}
    extra_param = "test_value"

    results = build_results(
        raw_json,
        method=mock_method,
        data_key="data",
        custom_arg=extra_param
    )

    assert results == ["processed_1", "processed_2", "processed_3"]
    assert mock_method.call_count == 3

    mock_method.assert_any_call(1, custom_arg=extra_param)


def test_build_results_with_limit():
    """Verify the limit parameter restricts the number of calls."""
    mock_method = MagicMock(return_value="ok")
    raw_json = [1, 2, 3, 4, 5]

    results = build_results(raw_json, method=mock_method, pure_data=True, limit=2)

    assert len(results) == 2
    assert mock_method.call_count == 2


def test_build_results_pure_data_true():
    """Verify that pure_data=True treats the input as the list itself."""
    mock_method = MagicMock(side_effect=lambda x: x * 10)
    raw_data = [1, 2]

    results = build_results(raw_data, method=mock_method, pure_data=True)

    assert results == [10, 20]


def test_build_results_empty_data():
    """Verify behavior when the data key is missing or empty."""
    mock_method = MagicMock()

    results = build_results({}, method=mock_method, data_key="non_existent")

    assert results == []
    mock_method.assert_not_called()

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

from unittest.mock import MagicMock

from _pytest.monkeypatch import MonkeyPatch

from siemplify_utilities.actions.QueryJoiner import main


def test_query_joiner_default_delimiter(monkeypatch: MonkeyPatch) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify.parameters = {
        "Values": "val1,val2,val3",
        "Query Field": "Field",
        "Query Operator": "OR",
    }
    monkeypatch.setattr(
        "siemplify_utilities.actions.QueryJoiner.SiemplifyAction",
        MagicMock(return_value=mock_siemplify),
    )

    main()

    mock_siemplify.end.assert_called_once()
    _, query = mock_siemplify.end.call_args[0]
    assert query == "Field=val1 OR Field=val2 OR Field=val3"


def test_query_joiner_custom_delimiter(monkeypatch: MonkeyPatch) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify.parameters = {
        "Values": "val1|val2|val3",
        "Query Field": "Field",
        "Query Operator": "OR",
        "Delimiter": "|",
    }
    monkeypatch.setattr(
        "siemplify_utilities.actions.QueryJoiner.SiemplifyAction",
        MagicMock(return_value=mock_siemplify),
    )

    main()

    mock_siemplify.end.assert_called_once()
    _, query = mock_siemplify.end.call_args[0]
    assert query == "Field=val1 OR Field=val2 OR Field=val3"


def test_query_joiner_complex_values_with_commas(monkeypatch: MonkeyPatch) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify.parameters = {
        "Values": "http://site.com?a=1,b=2~~~http://site.com?c=3",
        "Query Field": "URL",
        "Query Operator": "OR",
        "Delimiter": "~~~",
    }
    monkeypatch.setattr(
        "siemplify_utilities.actions.QueryJoiner.SiemplifyAction",
        MagicMock(return_value=mock_siemplify),
    )

    main()

    mock_siemplify.end.assert_called_once()
    _, query = mock_siemplify.end.call_args[0]
    assert query == "URL=http://site.com?a=1,b=2 OR URL=http://site.com?c=3"


def test_query_joiner_with_space_values_with_commas(monkeypatch: MonkeyPatch) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify.parameters = {
        "Values": "http://site.com?a=1,b=2 ~~~ http://site.com?c=3",
        "Query Field": "URL",
        "Query Operator": "OR",
        "Delimiter": "~~~",
    }
    monkeypatch.setattr(
        "siemplify_utilities.actions.QueryJoiner.SiemplifyAction",
        MagicMock(return_value=mock_siemplify),
    )

    main()

    mock_siemplify.end.assert_called_once()
    _, query = mock_siemplify.end.call_args[0]
    assert query == "URL=http://site.com?a=1,b=2  OR URL= http://site.com?c=3"


def test_query_joiner_empty_delimiter_fallback(monkeypatch: MonkeyPatch) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify.parameters = {
        "Values": "val1,val2,val3",
        "Query Field": "Field",
        "Query Operator": "OR",
        "Delimiter": "",
    }
    monkeypatch.setattr(
        "siemplify_utilities.actions.QueryJoiner.SiemplifyAction",
        MagicMock(return_value=mock_siemplify),
    )

    main()

    mock_siemplify.end.assert_called_once()
    _, query = mock_siemplify.end.call_args[0]
    assert query == "Field=val1 OR Field=val2 OR Field=val3"


def test_query_joiner_space_delimiter_fallback(monkeypatch: MonkeyPatch) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify.parameters = {
        "Values": "val1,val2,val3",
        "Query Field": "Field",
        "Query Operator": "OR",
        "Delimiter": "   ",
    }
    monkeypatch.setattr(
        "siemplify_utilities.actions.QueryJoiner.SiemplifyAction",
        MagicMock(return_value=mock_siemplify),
    )

    main()

    mock_siemplify.end.assert_called_once()
    _, query = mock_siemplify.end.call_args[0]
    assert query == "Field=val1 OR Field=val2 OR Field=val3"

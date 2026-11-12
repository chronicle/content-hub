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

import json
from unittest.mock import MagicMock

import pytest

from microsoft_teams.actions import WaitForReply as action


# pylint: disable=redefined-outer-name
@pytest.fixture
def mock_siemplify():
    siemplify = MagicMock()
    siemplify.result = MagicMock()
    return siemplify


def test_check_expected_reply_with_none_value(mock_siemplify):
    """
    Verify that expected_reply=None does not raise TypeError.
    """
    result_data = json.dumps({"result": []})

    try:
        action.check_expected_reply(
            siemplify=mock_siemplify,
            wait_method="CHECK_FIRST_REPLY",
            expected_reply=None,
            result_data=result_data,
            is_timeout=False
        )
    except TypeError as e:
        pytest.fail(f"check_expected_reply raised TypeError with None input: {e}")


def test_check_expected_reply_unicode_escape(mock_siemplify):
    """
    Verify that unicode escaped characters are decoded correctly.
    """
    expected_reply = "\\u2713"
    action.get_content_values = MagicMock(return_value=["✓"])

    result_data = json.dumps({"result": [{"content": "✓"}]})

    _, result, _ = action.check_expected_reply(
        siemplify=mock_siemplify,
        wait_method="CHECK_FIRST_REPLY",
        expected_reply=expected_reply,
        result_data=result_data
    )

    assert result == '{"result": [{"content": "\\u2713"}]}'


def test_check_expected_reply_timeout_logic(mock_siemplify):
    """
    Verify that the function returns the correct status on timeout.
    """
    result_data = json.dumps({"result": []})

    output_message, result, status = action.check_expected_reply(
        siemplify=mock_siemplify,
        wait_method="CHECK_FIRST_REPLY",
        expected_reply="test",
        result_data=result_data,
        is_timeout=True
    )

    assert status == action.EXECUTION_STATE_TIMEDOUT
    assert result is False
    assert output_message == action.TIMEOUT_MESSAGE

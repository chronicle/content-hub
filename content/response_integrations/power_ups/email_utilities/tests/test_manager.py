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

from unittest.mock import MagicMock

from ..core.EmailManager import EmailManager

EDGE_CASE_EMAIL = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Edge Case
Message-ID: <[bdef3479a5a642f28f71ce85c707eaa8-...@microsoft.com]>

This is the body of the email.
"""

COMMON_CASE_EMAIL = b"""From: sender@example.com
To: recipient@example.com
Subject: Valid Email
Message-ID: <valid-id@example.com>

This is a valid email body.
"""


def test_msg_parsing_edge_case() -> None:
    """Test parsing of an email with a malformed Message-ID header."""
    result = EmailManager(
        siemplify=MagicMock(),
        logger=MagicMock(),
        custom_regex={},
    ).parse_email('sample.eml', EDGE_CASE_EMAIL)

    assert result is not None
    assert "result" in result

    headers = result["result"]["header"]
    assert headers["subject"] == "Test Edge Case"
    assert headers["from"] == "sender@example.com"
    assert headers["to"] == ["recipient@example.com"]


def test_msg_parsing_common_case() -> None:
    """Test parsing of a standard email with valid headers."""
    result = EmailManager(
        siemplify=MagicMock(),
        logger=MagicMock(),
        custom_regex={},
    ).parse_email('sample.eml', COMMON_CASE_EMAIL)

    assert result is not None
    assert "result" in result

    headers = result["result"]["header"]
    assert headers["subject"] == "Valid Email"
    assert headers["from"] == "sender@example.com"
    assert headers["to"] == ["recipient@example.com"]

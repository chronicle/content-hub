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

from ..actions.ParseBase64Email import body as parse_base64_body
from ..core.EmailManager import EmailBody, EmailManager, EmailUtils
from ..core.EmailParser import EmlParser
from ..core.EmailUtilitiesManager import fix_malformed_eml_content

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

SURROGATE_EMAIL = (
    "From: sender@example.com\n"
    "To: recipient@example.com\n"
    "Subject: Test Surrogate Edge Case\n"
    "Message-ID: <surrogate-id@example.com>\n"
    "Content-Type: text/plain; charset=utf-8\n"
    "\n"
    "This is the body with surrogate \ud800 and \udcff test.\n"
).encode("utf-8", errors="surrogatepass")


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


def test_msg_parsing_surrogate_characters() -> None:
    """Test parsing of an email containing surrogate characters."""
    result = EmailManager(
        siemplify=MagicMock(),
        logger=MagicMock(),
        custom_regex={},
    ).parse_email('sample.eml', SURROGATE_EMAIL)

    assert result is not None
    assert "result" in result
    assert "body" in result["result"]
    assert len(result["result"]["body"]) > 0
    assert "hash" in result["result"]["body"][0]
    assert len(result["result"]["body"][0]["hash"]) == 64


def test_email_body_hash_with_surrogates() -> None:
    """Test EmailBody.body handles surrogate characters without UnicodeEncodeError."""
    body_handler = EmailBody(logger=MagicMock(), email_utils=EmailUtils({}))
    surrogate_text = "Message with lone surrogate \ud800 and \udcff content."
    result = body_handler.body(surrogate_text, "text/plain")

    assert result["content"] == surrogate_text
    assert result["content_type"] == "text/plain"
    assert len(result["hash"]) == 64


def test_eml_parser_wrap_hash_sha256_with_surrogates() -> None:
    """Test EmlParser.wrap_hash_sha256 handles surrogate characters without error."""
    surrogate_text = "String with surrogate \ud800\udcff"
    hash_output = EmlParser.wrap_hash_sha256(surrogate_text)

    assert isinstance(hash_output, str)
    assert len(hash_output) == 64


def test_eml_parser_decode_email_bytes_with_surrogates() -> None:
    """Test EmlParser.decode_email_bytes handles surrogate characters in body."""
    parser = EmlParser(include_raw_body=True)
    parsed = parser.decode_email_bytes(SURROGATE_EMAIL)

    assert parsed is not None
    assert "body" in parsed
    assert len(parsed["body"]) > 0
    first_body = parsed["body"][0]
    assert "hash" in first_body
    assert len(first_body["hash"]) == 64


def test_parse_base64_email_body_with_surrogates() -> None:
    """Test ParseBase64Email.body handles surrogate characters properly."""
    surrogate_text = "Base64 email body with \ud800 surrogate characters."
    result = parse_base64_body(surrogate_text, "text/plain")

    assert result["content"] == surrogate_text
    assert len(result["hash"]) == 64


def test_fix_malformed_eml_content_with_surrogates() -> None:
    """Test fix_malformed_eml_content handles surrogate bytes without error."""
    fixed = fix_malformed_eml_content(SURROGATE_EMAIL)

    assert isinstance(fixed, bytes)
    assert len(fixed) > 0


def test_mime_part_surrogate_encoding() -> None:
    """Test encoding MIME parts containing surrogate characters with surrogatepass."""
    import base64
    from email import message_from_bytes

    msg = message_from_bytes(SURROGATE_EMAIL)
    encoded = base64.b64encode(
        msg.as_string().encode("utf-8", errors="surrogatepass"),
    ).decode("utf-8")

    assert isinstance(encoded, str)
    assert len(encoded) > 0




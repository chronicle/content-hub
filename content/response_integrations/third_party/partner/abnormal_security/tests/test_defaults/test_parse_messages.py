from __future__ import annotations

import pytest

from ...core.AbnormalManager import AbnormalValidationError, parse_messages_input


class TestParseMessagesInput:
    def test_json_array_passthrough(self) -> None:
        raw = '[{"raw_message_id": "AAMkAGI2THVSAAA=", "subject": "Phishing"}]'
        assert parse_messages_input(raw) == [{"raw_message_id": "AAMkAGI2THVSAAA=", "subject": "Phishing"}]

    def test_single_json_object_is_wrapped(self) -> None:
        raw = '{"raw_message_id": "AAMkAGI2THVSAAA="}'
        assert parse_messages_input(raw) == [{"raw_message_id": "AAMkAGI2THVSAAA="}]

    def test_bare_string_id_builds_message_object(self) -> None:
        assert parse_messages_input("4551618356913732076") == [{"message_id": "4551618356913732076"}]

    def test_bare_integer_id_preserves_precision(self) -> None:
        # A 19-digit ID parses as a JSON int; Python ints are arbitrary precision,
        # so str() round-trips the exact value with no float loss.
        assert parse_messages_input("4551618356913732076") == [{"message_id": "4551618356913732076"}]

    def test_scientific_notation_is_rejected(self) -> None:
        # A 64-bit ID passed as a number arrives as a lossy float; reject it and
        # point the analyst at the string message-ID placeholder.
        with pytest.raises(AbnormalValidationError, match="lost precision"):
            parse_messages_input("-1.0879728147833105e+18")

    def test_empty_input_is_rejected(self) -> None:
        with pytest.raises(AbnormalValidationError, match="required"):
            parse_messages_input("")

    def test_whitespace_only_input_is_rejected(self) -> None:
        with pytest.raises(AbnormalValidationError, match="required"):
            parse_messages_input("   ")

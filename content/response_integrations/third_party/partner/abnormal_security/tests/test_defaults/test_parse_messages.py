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

    def test_non_json_bare_id_is_rejected(self) -> None:
        # A non-JSON bare identifier hits the JSONDecodeError path; still insufficient.
        with pytest.raises(AbnormalValidationError, match="Remediate Threat"):
            parse_messages_input("AAMkAGI2THVSAAA=")

    def test_bare_json_scalar_is_rejected(self) -> None:
        # A JSON-parseable integer is still just an ID — insufficient for the schema.
        with pytest.raises(AbnormalValidationError, match="Remediate Threat"):
            parse_messages_input("4551618356913732076")

    def test_scientific_notation_is_rejected(self) -> None:
        # A 64-bit ID passed as a number arrives as a lossy float.
        with pytest.raises(AbnormalValidationError, match="lost precision"):
            parse_messages_input("-1.0879728147833105e+18")

    def test_empty_input_is_rejected(self) -> None:
        with pytest.raises(AbnormalValidationError, match="required"):
            parse_messages_input("")

    def test_whitespace_only_input_is_rejected(self) -> None:
        with pytest.raises(AbnormalValidationError, match="required"):
            parse_messages_input("   ")

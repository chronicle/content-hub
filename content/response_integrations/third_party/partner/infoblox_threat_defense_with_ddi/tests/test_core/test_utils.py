from __future__ import annotations

import pytest

from ...core.InfobloxExceptions import InfobloxException, InvalidIntegerException
from ...core.utils import (
    add_additional_params_to_payload,
    clean_params,
    convert_to_rfc3339,
    get_nullable_field,
    is_empty_string,
    parse_and_validate_int_list,
    parse_rules_param,
    parse_tags,
    string_to_list,
    truncate_json_for_display,
    validate_enum,
    validate_indicators,
    validate_integer_param,
    validate_required_string,
)


class TestCleanParams:
    def test_removes_none_values(self) -> None:
        assert clean_params({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}

    def test_keeps_falsy_non_none_values(self) -> None:
        assert clean_params({"a": 0, "b": "", "c": False}) == {"a": 0, "b": "", "c": False}

    def test_empty_dict(self) -> None:
        assert clean_params({}) == {}


class TestIsEmptyString:
    @pytest.mark.parametrize("value", ["empty", "Empty", "EMPTY", "  empty  "])
    def test_matches_case_and_whitespace_insensitively(self, value: str) -> None:
        assert is_empty_string(value) is True

    def test_non_empty_string_is_false(self) -> None:
        assert is_empty_string("something") is False

    @pytest.mark.parametrize("value", [None, 123, [], {}])
    def test_non_string_types_are_false(self, value) -> None:
        assert is_empty_string(value) is False


class TestGetNullableField:
    def test_no_value_returns_existing(self) -> None:
        assert get_nullable_field(None, "existing") == "existing"
        assert get_nullable_field("", "existing") == "existing"

    def test_empty_sentinel_returns_none(self) -> None:
        assert get_nullable_field("empty", "existing") is None

    def test_value_returned_as_is_without_parser(self) -> None:
        assert get_nullable_field("new-value", "existing") == "new-value"

    def test_value_passed_through_parser(self) -> None:
        assert get_nullable_field("3", "existing", parser=int) == 3


class TestParseAndValidateIntList:
    def test_none_returns_none(self) -> None:
        assert parse_and_validate_int_list(None, "Field") is None

    def test_empty_sentinel_returns_empty_list(self) -> None:
        assert parse_and_validate_int_list("empty", "Field") == []

    def test_valid_csv_returns_int_list(self) -> None:
        assert parse_and_validate_int_list("1, 2, 3", "Field") == [1, 2, 3]

    def test_invalid_entry_raises(self) -> None:
        with pytest.raises(InvalidIntegerException):
            parse_and_validate_int_list("1, abc", "Field")


class TestParseRulesParam:
    def test_none_returns_none(self) -> None:
        assert parse_rules_param(None) is None

    def test_valid_json_array_returned(self) -> None:
        rules = '[{"action": "block"}]'
        assert parse_rules_param(rules) == [{"action": "block"}]

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Rules must be a valid JSON array"):
            parse_rules_param("not-json")


class TestAddAdditionalParamsToPayload:
    def test_no_additional_params_returns_payload_unchanged(self) -> None:
        payload = {"name": "policy"}
        assert add_additional_params_to_payload(payload, None) == {"name": "policy"}

    def test_allowed_keys_are_merged(self) -> None:
        payload = {"name": "policy"}
        result = add_additional_params_to_payload(payload, '{"precedence": 1, "ecs": true}')
        assert result == {"name": "policy", "precedence": 1, "ecs": True}

    def test_unsupported_key_raises_infoblox_exception(self) -> None:
        with pytest.raises(InfobloxException, match="Unsupported key"):
            add_additional_params_to_payload({}, '{"bogus_key": 1}')

    def test_non_object_json_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="must be a JSON object"):
            add_additional_params_to_payload({}, "[1, 2, 3]")

    def test_invalid_json_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="must be a JSON object"):
            add_additional_params_to_payload({}, "not-json")


class TestValidateIndicators:
    @pytest.mark.parametrize(
        "item",
        ["192.168.1.1", "10.0.0.0/24", "example.com", "sub.example.co.uk", "2001:db8::1"],
    )
    def test_valid_items_pass(self, item: str) -> None:
        assert validate_indicators([item]) == [item]

    def test_invalid_item_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid IPv4, IPv6, or domain"):
            validate_indicators(["not_a_valid_indicator!!"])


class TestValidateRequiredString:
    def test_valid_string_returned(self) -> None:
        assert validate_required_string("value", "Field") == "value"

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_missing_value_raises(self, value) -> None:
        with pytest.raises(ValueError, match="Field must be a non-empty string"):
            validate_required_string(value, "Field")


class TestValidateIntegerParam:
    def test_valid_positive_integer(self) -> None:
        assert validate_integer_param("5", "Field") == 5

    def test_non_integer_raises(self) -> None:
        with pytest.raises(InvalidIntegerException, match="must be an integer"):
            validate_integer_param("abc", "Field")

    def test_negative_rejected_by_default(self) -> None:
        with pytest.raises(InvalidIntegerException, match="non-negative"):
            validate_integer_param("-1", "Field")

    def test_negative_allowed_when_flagged(self) -> None:
        assert validate_integer_param("-1", "Field", allow_negative=True) == -1

    def test_zero_rejected_by_default(self) -> None:
        with pytest.raises(InvalidIntegerException, match="greater than zero"):
            validate_integer_param("0", "Field")

    def test_zero_allowed_when_flagged(self) -> None:
        assert validate_integer_param("0", "Field", zero_allowed=True) == 0


class TestStringToList:
    def test_none_returns_empty_list(self) -> None:
        assert string_to_list(None) == []

    def test_empty_string_returns_empty_list(self) -> None:
        assert string_to_list("") == []

    def test_csv_is_split_and_trimmed(self) -> None:
        assert string_to_list(" a, b ,c") == ["a", "b", "c"]

    def test_blank_entries_are_dropped(self) -> None:
        assert string_to_list("a,,b, ,") == ["a", "b"]


class TestParseTags:
    def test_none_returns_none(self) -> None:
        assert parse_tags(None) is None

    def test_valid_json_object_returned(self) -> None:
        assert parse_tags('{"env": "prod"}') == {"env": "prod"}

    def test_non_object_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Tags must be a valid JSON object"):
            parse_tags("[1, 2]")

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Tags must be a valid JSON object"):
            parse_tags("not-json")


class TestTruncateJsonForDisplay:
    def test_short_json_not_truncated(self) -> None:
        data = {"a": 1}
        assert truncate_json_for_display(data) == '{"a": 1}'

    def test_long_json_is_truncated_with_suffix(self) -> None:
        data = {"a": "x" * 500}
        result = truncate_json_for_display(data, max_chars=50)
        assert len(result) == 50 + len("... [truncated]")
        assert result.endswith("... [truncated]")

    def test_non_serializable_data_returns_error_message(self) -> None:
        result = truncate_json_for_display(object())
        assert result.startswith("[Invalid JSON]")


class TestValidateEnum:
    def test_allowed_value_returned(self) -> None:
        assert validate_enum("HIGH", ["LOW", "HIGH"], "Field") == "HIGH"

    def test_none_is_allowed(self) -> None:
        assert validate_enum(None, ["LOW", "HIGH"], "Field") is None

    def test_disallowed_value_raises(self) -> None:
        with pytest.raises(ValueError, match="Field must be one of"):
            validate_enum("MEDIUM", ["LOW", "HIGH"], "Field")


class TestValidateRfc3339Datetime:
    def test_none_returns_none(self) -> None:
        assert convert_to_rfc3339(None, "Field") is None

    def test_empty_string_returned_unchanged(self) -> None:
        assert convert_to_rfc3339("", "Field") == ""

    def test_valid_zulu_datetime_returned_unchanged(self) -> None:
        value = "12/19/2025 07:01:56"
        assert convert_to_rfc3339(value, "Field") == "2025-12-19T07:01:56Z"

    def test_invalid_datetime_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a valid RFC 3339 date-time"):
            convert_to_rfc3339("not-a-date", "Field")

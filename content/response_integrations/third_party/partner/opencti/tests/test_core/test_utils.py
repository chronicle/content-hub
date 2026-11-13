from __future__ import annotations

from ...core.utils import convert_date_format, parse_csv_list


class TestConvertDateFormat:
    def test_iso_with_timezone_returns_utc(self):
        result = convert_date_format("2024-01-15T10:30:00+02:00")
        assert result == "2024-01-15T08:30:00+00:00"

    def test_utc_string_unchanged(self):
        result = convert_date_format("2024-06-01T00:00:00+00:00")
        assert result == "2024-06-01T00:00:00+00:00"

    def test_naive_date_string_is_parsed(self):
        result = convert_date_format("2024-03-20T12:00:00")
        assert result.endswith("+00:00")
        assert "2024-03-20" in result

    def test_output_format_is_correct(self):
        result = convert_date_format("2024-01-01T00:00:00Z")
        assert result == "2024-01-01T00:00:00+00:00"

    def test_google_soar_utc_suffix_is_supported(self):
        result = convert_date_format("2026-06-16 08:00:00 UTC+00")
        assert result == "2026-06-16T08:00:00+00:00"


class TestParseCsvList:
    def test_basic_csv(self):
        assert parse_csv_list("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace(self):
        assert parse_csv_list("  a , b , c  ") == ["a", "b", "c"]

    def test_none_returns_empty(self):
        assert parse_csv_list(None) == []

    def test_empty_string_returns_empty(self):
        assert parse_csv_list("") == []

    def test_single_item(self):
        assert parse_csv_list("label1") == ["label1"]

    def test_skips_blank_entries(self):
        assert parse_csv_list("a,,b, ,c") == ["a", "b", "c"]

    def test_custom_separator(self):
        assert parse_csv_list("a|b|c", separator="|") == ["a", "b", "c"]

    def test_whitespace_only_string_returns_empty(self):
        assert parse_csv_list("   ") == []

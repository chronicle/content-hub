from __future__ import annotations

import json
from typing import Any

from tanium.core.datamodels import QuestionResultFullData


def test_question_result_init_parses_columns(question_result: QuestionResultFullData):
    """Tests that the last column ("Count") is removed."""
    assert len(question_result.columns) == 2

    assert question_result.columns == ["IP Address", "Computer Name"]


def test_question_result_init_parses_rows(question_result: QuestionResultFullData):
    """Tests that the last data element from each row is removed."""
    assert len(question_result.rows) == 3

    # --- Check Row 0 ---
    # The "Count" column must be removed, so inner 'data' length is 2
    assert len(question_result.rows[0]) == 2

    # Row 0, Column 0 (IP Address)
    expected_r0_c0 = ["fe80::obfuscated:1", "192.168.1.100"]
    assert question_result.rows[0][0] == expected_r0_c0

    # Row 0, Column 1 (Computer Name)
    expected_r0_c1 = ["workstation-001"]
    assert question_result.rows[0][1] == expected_r0_c1

    # --- Check Row 1 ---
    assert len(question_result.rows[1]) == 2  # Check inner length

    # Row 1, Column 0 (IP Address)
    expected_r1_c0 = ["fe80::obfuscated:2", "192.168.1.101"]
    assert question_result.rows[1][0] == expected_r1_c0

    # Row 1, Column 1 (Computer Name)
    expected_r1_c1 = ["workstation-002"]
    assert question_result.rows[1][1] == expected_r1_c1

    # --- Check Row 2 ---
    assert len(question_result.rows[2]) == 2  # Check inner length

    # Row 2, Column 0 (IP Address)
    expected_r2_c0 = ["10.10.10.50"]
    assert question_result.rows[2][0] == expected_r2_c0

    # Row 2, Column 1 (Computer Name)
    expected_r2_c1 = ["linux-server-prod.internal"]
    assert question_result.rows[2][1] == expected_r2_c1


def test_question_result_init_empty_raw_data():
    """Tests initialization with completely empty raw data."""
    result = QuestionResultFullData.from_raw_response(raw_data={})
    assert result.rows == []
    assert result.columns == []
    assert result.raw_data == {}

    assert result.to_json() == "{}"
    assert not result.to_csv_lines()


def test_question_result_init_empty_result_sets():
    """Tests initialization when the raw data contains an empty 'result_sets' list."""
    result = QuestionResultFullData.from_raw_response(
        raw_data={"data": {"result_sets": []}}
    )
    assert result.rows == []
    assert result.columns == []
    assert result.raw_data == {}

    assert result.to_json() == "{}"
    assert not result.to_csv_lines()


def test_question_result_to_json_format_and_structure(
    question_result: QuestionResultFullData,
):
    """Tests the output format and structure of the to_json method."""
    json_str = question_result.to_json()
    data = json.loads(json_str)

    assert "id" in data

    assert len(data["columns"]) == 2
    column_names = [col.get("name") for col in data["columns"]]
    assert column_names == ["IP Address", "Computer Name"]

    expected_rows = [
        {
            "IP Address": ["fe80::obfuscated:1", "192.168.1.100"],
            "Computer Name": ["workstation-001"],
        },
        {
            "IP Address": ["fe80::obfuscated:2", "192.168.1.101"],
            "Computer Name": ["workstation-002"],
        },
        {
            "IP Address": ["10.10.10.50"],
            "Computer Name": ["linux-server-prod.internal"],
        },
    ]
    assert data["rows"] == expected_rows


def test_question_result_json_limit_1(
    question_result_raw_data: dict[str, Any]
):
    """Tests that the to_json method respects the 'limit' parameter."""
    json_str = QuestionResultFullData.from_raw_response(
        raw_data=question_result_raw_data, limit=1
    ).to_json()

    data = json.loads(json_str)

    assert "id" in data

    assert len(data["columns"]) == 2
    column_names = [col.get("name") for col in data["columns"]]
    assert column_names == ["IP Address", "Computer Name"]

    expected_rows = [
        {
            "IP Address": ["fe80::obfuscated:1", "192.168.1.100"],
            "Computer Name": ["workstation-001"],
        }
    ]
    assert data["rows"] == expected_rows


def test_question_result_to_csv_lines_default_delimiter(
    question_result: QuestionResultFullData,
):
    """Tests CSV conversion with the default multi-value delimiter."""
    csv_lines = question_result.to_csv_lines()

    expected_csv_lines = [
        {
            "Computer Name": "workstation-001",
            "IP Address": "fe80::obfuscated:1, 192.168.1.100",
        },
        {
            "Computer Name": "workstation-002",
            "IP Address": "fe80::obfuscated:2, 192.168.1.101",
        },
        {
            "Computer Name": "linux-server-prod.internal",
            "IP Address": "10.10.10.50",
        },
    ]

    assert csv_lines == expected_csv_lines


def test_question_result_to_csv_lines_custom_delimiter(
    question_result: QuestionResultFullData,
):
    """Tests CSV conversion with a custom multi-value delimiter."""
    csv_lines = question_result.to_csv_lines(multi_value_delimiter="|")

    expected_csv_lines = [
        {
            "Computer Name": "workstation-001",
            "IP Address": "fe80::obfuscated:1|192.168.1.100",
        },
        {
            "Computer Name": "workstation-002",
            "IP Address": "fe80::obfuscated:2|192.168.1.101",
        },
        {
            "Computer Name": "linux-server-prod.internal",
            "IP Address": "10.10.10.50",
        },
    ]

    assert csv_lines == expected_csv_lines


def test_question_result_csv_limit_1(question_result_raw_data: dict[str, Any]):
    """Tests that the to_csv_lines method respects the 'limit' parameter."""
    csv_lines = QuestionResultFullData.from_raw_response(
        raw_data=question_result_raw_data, limit=1
    ).to_csv_lines()

    expected_csv_lines = [
        {
            "Computer Name": "workstation-001",
            "IP Address": "fe80::obfuscated:1, 192.168.1.100"
        }
    ]

    assert csv_lines == expected_csv_lines

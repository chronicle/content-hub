from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, List, Optional, TypeAlias
from unittest.mock import Mock

import pytest
from TIPCommon.types import SingleJson
from google_threat_intelligence.core.utils import (
    adjust_time,
    assess_risk,
    get_search_window_total,
    parse_entity_filters,
    prepare_entity_filter,
)


# Test for allow/block lists
TestEntity: TypeAlias = dict[str, str]


@pytest.fixture(name="input_data")
def create_input_data() -> list[TestEntity]:
    values = ["A", "BB", "CCC", "A", "B", "DDDD"]
    return list(map(lambda v: {"value": v}, values))


def extractor(v: TestEntity) -> str:
    return v["value"]


def assert_equals_ignore_order(actual: list[str], expected: list[str]) -> None:
    actual = list(sorted(actual))
    expected = list(sorted(expected))
    assert actual == expected


def run_with_filter(filters: set[str], input_data: list[TestEntity]) -> list[str]:
    """
    Runs the WHEN part of test
    Args:
        filters: List of string filters
        input_data: Input data from fixture

    Returns: Filtered input data (flattened)

    """
    allow_list, block_list = parse_entity_filters(filters)
    filter_predicate = prepare_entity_filter(
        extractor=extractor, allow_list=allow_list, block_list=block_list
    )

    result = filter(filter_predicate, input_data)
    result = map(extractor, result)
    return list(result)


def test_allowed_list_only(input_data: list[TestEntity]):
    filters = {"A", "CCC", "G"}
    result = run_with_filter(filters, input_data)
    assert_equals_ignore_order(result, ["A", "A", "CCC"])


def test_blocked_list_only(input_data: list[TestEntity]):
    filters = {"!A", "!G", "!CCC"}
    result = run_with_filter(filters, input_data)
    assert_equals_ignore_order(result, ["BB", "B", "DDDD"])


def test_no_filter(input_data: list[TestEntity]):
    filters = set()
    result = run_with_filter(filters, input_data)
    assert_equals_ignore_order(result, ["A", "A", "B", "DDDD", "BB", "CCC"])


def test_allowed_and_blocked_should_ignore_blocked(input_data: list[TestEntity]):
    filters = {"A", "!A", "!G", "CCC", "G", "!DDDD"}
    result = run_with_filter(filters, input_data)
    assert_equals_ignore_order(result, ["A", "A", "CCC"])


@dataclass
class AssessRiskParams:
    """
    A class to hold parameters for assess_risk tests
    """

    ioc_data: Any
    expected_result: bool
    gti_score: Optional[int] = None
    engine_threshold: Optional[int] = None
    engine_percentage_threshold: Optional[int] = None
    engine_allowlist: Optional[List[str]] = None


ASSESS_RISK_TEST_CASES = [
    AssessRiskParams(
        ioc_data=Mock(verdict="VERDICT_SUSPICIOUS", threat_score=0),
        expected_result=True,
    ),
    AssessRiskParams(
        ioc_data=Mock(verdict="VERDICT_HARMLESS", threat_score=0),
        expected_result=False,
    ),
    AssessRiskParams(
        ioc_data=Mock(verdict="VERDICT_HARMLESS", threat_score=80),
        gti_score=70,
        expected_result=True,
    ),
    AssessRiskParams(
        ioc_data=Mock(verdict="VERDICT_HARMLESS", threat_score=60),
        gti_score=70,
        expected_result=False,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious"},
                "engine2": {"category": "malicious"},
            },
        ),
        engine_threshold=2,
        expected_result=True,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious"},
                "engine2": {"category": "harmless"},
            },
        ),
        engine_threshold=2,
        expected_result=False,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious"},
                "engine2": {"category": "harmless"},
            },
        ),
        engine_percentage_threshold=50,
        expected_result=True,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious"},
                "engine2": {"category": "harmless"},
            },
        ),
        engine_percentage_threshold=60,
        expected_result=False,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious", "engine_name": "e1"},
                "engine2": {"category": "malicious", "engine_name": "e2"},
            },
        ),
        engine_threshold=2,
        engine_allowlist=["e1"],
        expected_result=False,
    ),
    AssessRiskParams(
        ioc_data=Mock(verdict="VERDICT_MALICIOUS", threat_score=0),
        expected_result=True,
    ),
    AssessRiskParams(
        ioc_data=Mock(verdict="VERDICT_HARMLESS", threat_score=0),
        expected_result=False,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious"},
                "engine2": {"category": "harmless"},
            },
        ),
        engine_threshold=2,
        engine_percentage_threshold=50,
        expected_result=False,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious"},
                "engine2": {"category": "malicious"},
            },
        ),
        engine_threshold=2,
        engine_percentage_threshold=40,
        expected_result=True,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious", "engine_name": "e1"},
                "engine2": {"category": "harmless", "engine_name": "e2"},
            },
        ),
        engine_threshold=1,
        engine_allowlist=["e1", "e2"],
        expected_result=True,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious", "engine_name": "e1"},
                "engine2": {"category": "harmless", "engine_name": "e2"},
            },
        ),
        engine_percentage_threshold=50,
        engine_allowlist=["e1", "e2"],
        expected_result=True,
    ),
    AssessRiskParams(
        ioc_data=Mock(
            verdict="VERDICT_HARMLESS",
            threat_score=0,
            last_analysis_results={
                "engine1": {"category": "malicious", "engine_name": "e1"},
                "engine2": {"category": "harmless", "engine_name": "e2"},
            },
        ),
        engine_percentage_threshold=51,
        engine_allowlist=["e1", "e2"],
        expected_result=False,
    ),
]


@pytest.mark.parametrize(
    "test_case",
    ASSESS_RISK_TEST_CASES,
    ids=[
        "verdict is suspicious",
        "verdict is not suspicious",
        "GTI score is high enough",
        "GTI score is too low",
        "Engine threshold is met",
        "Engine threshold is not met",
        "Engine percentage threshold is met",
        "Engine percentage threshold is not met",
        "Engine allowlist is used",
        "Default case, verdict is suspicious",
        "Default case, verdict is not suspicious",
        "Engine threshold overrides percentage - percentage met,"
        " threshold not (now False)",
        "Engine threshold overrides percentage - threshold met,"
        " percentage not (still True)",
        "Engine threshold with allowlist - met",
        "Engine percentage threshold with allowlist - met",
        "Engine percentage threshold with allowlist - not met",
    ],
)
def test_assess_risk(test_case: AssessRiskParams):
    logger = Mock()
    result = assess_risk(
        ioc_data=test_case.ioc_data,
        gti_score=test_case.gti_score,
        engine_threshold=test_case.engine_threshold,
        engine_percentage_threshold=test_case.engine_percentage_threshold,
        engine_allowlist=test_case.engine_allowlist,
        logger=logger,
    )
    assert result == test_case.expected_result


@pytest.mark.parametrize(
    ("hours", "expected"),
    [
        (None, datetime(2026, 10, 6, 16, 0, 0)),
        (12, datetime(2026, 10, 6, 22, 0, 0)),
        (0.5, datetime(2026, 10, 6, 10, 30, 0)),
    ],
    ids=["default 6 hours", "custom hours", "fractional hours"],
)
def test_adjust_time_adds_hours(hours: float | None, expected: datetime) -> None:
    now = datetime(2026, 10, 7, 0, 0, 0)
    kwargs = {} if hours is None else {"hours": hours}

    assert adjust_time("2026-10-06T10:00:00Z", now=now, **kwargs) == expected


def test_adjust_time_is_capped_to_now() -> None:
    now = datetime(2026, 10, 6, 11, 0, 0)

    assert adjust_time("2026-10-06T10:00:00Z", hours=6, now=now) == now


def test_adjust_time_defaults_to_current_time() -> None:
    before = datetime.utcnow()

    result = adjust_time(before.strftime("%Y-%m-%dT%H:%M:%SZ"), hours=1000)

    assert before - timedelta(seconds=1) <= result <= datetime.utcnow()


@pytest.mark.parametrize(
    ("search_result", "expected_total"),
    [
        ({"total_hits": 5000, "total_pages": 50, "hits": [{"id": "a"}]}, 5000),
        ({"total": 42, "hits": []}, 42),
        ({"total_hits": None, "total": "7", "hits": [{"id": "a"}, {"id": "b"}]}, 2),
        ({"total_hits": True, "hits": [{"id": "a"}]}, 1),
        ({"hits": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}, 3),
        ({}, 0),
    ],
)
def test_get_search_window_total_prefers_the_live_total_hits_key(
    search_result: SingleJson,
    expected_total: int,
) -> None:
    assert get_search_window_total(search_result) == expected_total

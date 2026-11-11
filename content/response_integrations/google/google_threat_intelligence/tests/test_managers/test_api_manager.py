from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from soar_sdk.SiemplifyUtils import unix_now

import api_data_parser as parser
from google_threat_intelligence.core.api_manager import ApiManager
from google_threat_intelligence.core.api_utils import get_full_url
from google_threat_intelligence.core.constants import (
    ASM_ISSUES_INITIAL_WINDOW_HOURS,
    ASM_ISSUES_MAX_WINDOW_HOURS,
    ASM_ISSUES_MAX_WINDOW_PROBES,
    ASM_ISSUES_MIN_WINDOW_HOURS,
    ASM_ISSUES_TIME_FORMAT,
    ASM_ISSUES_WINDOW_RESULTS_CEILING,
)
from google_threat_intelligence.core.data_models import ASMIssue
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
    get_asm_query_value,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.responses.api.common_responses import (
    create_asm_issue,
)

API_ROOT: str = "https://www.virustotal.com"
NOW: datetime = datetime(2026, 10, 6, 12, 0, 0)
LIMIT: int = 10


def hours_ago(hours: float) -> str:
    return (NOW - timedelta(hours=hours)).strftime(ASM_ISSUES_TIME_FORMAT)


def get_search_windows(session: GoogleThreatIntelligenceSession) -> list[tuple[str, str]]:
    """Get the (last_seen_after, last_seen_before) pairs of the probed windows"""
    windows: list[tuple[str, str]] = []
    for record in session.request_history:
        path: str = record.request.url.path
        if "/asm/search/issues/" in path and record.request.params["page"] == ["0"]:
            windows.append(
                (
                    get_asm_query_value(path, "last_seen_after"),
                    get_asm_query_value(path, "last_seen_before"),
                )
            )

    return windows


def get_issues(manager: ApiManager, last_seen_after: str, **kwargs) -> list[ASMIssue]:
    return manager.get_issues(
        severity="",
        limit=LIMIT,
        last_seen_after=last_seen_after,
        status_filter=["open"],
        issue_name_filter=kwargs.pop("issue_name_filter", set()),
        siemplify=Mock(),
        **kwargs,
    )


def search_issues_url(last_seen_after: str) -> str:
    return get_full_url(
        API_ROOT, "search_issues", query_string=f"last_seen_after:{last_seen_after} "
    )


@pytest.fixture(name="manager")
def create_manager(
    script_session: GoogleThreatIntelligenceSession,
    mocker: MockerFixture,
) -> ApiManager:
    """Create an ApiManager with a mocked logger and `utcnow` pinned to NOW"""
    mocked_datetime = mocker.patch("api_manager.datetime", wraps=datetime)
    mocked_datetime.utcnow.return_value = NOW
    return ApiManager(
        api_root=API_ROOT,
        session=script_session,
        asm_project_name="",
        logger=Mock(),
    )


def test_get_issues_returns_issues_from_the_first_window(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    google_threat_intelligence_product.add_asm_issues(
        [
            create_asm_issue("issue-2", last_seen=hours_ago(8)),
            create_asm_issue("issue-1", last_seen=hours_ago(9)),
        ]
    )

    issues = get_issues(manager, last_seen_after=hours_ago(10))

    assert [issue.issue_id for issue in issues] == ["issue-1", "issue-2"]
    assert get_search_windows(script_session) == [(hours_ago(10), hours_ago(4))]
    assert manager.empty_scan_end is None


def test_get_issues_skips_empty_windows_with_a_growing_window(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    google_threat_intelligence_product.add_asm_issues(
        [create_asm_issue("issue-1", last_seen=hours_ago(5))]
    )

    issues = get_issues(manager, last_seen_after=hours_ago(100))

    assert [issue.issue_id for issue in issues] == ["issue-1"]
    assert get_search_windows(script_session) == [
        (hours_ago(100), hours_ago(94)),
        (hours_ago(94), hours_ago(82)),
        (hours_ago(82), hours_ago(58)),
        (hours_ago(58), hours_ago(10)),
        (hours_ago(10), hours_ago(0)),
    ]
    assert manager.empty_scan_end == hours_ago(10)
    manager.logger.info.assert_any_call(
        f"No new issues were found between {hours_ago(100)} and {hours_ago(94)} "
        "(issues in window: 0)."
    )
    manager.logger.info.assert_any_call("Continuing the search with a 12 hour window.")
    summaries = [
        call.args[0]
        for call in manager.logger.info.call_args_list
        if call.args[0].startswith("Issues in the window")
    ]
    assert summaries == [
        "Issues in the window: 1 (already ingested: 0, filtered out by name: 0, new: 1)."
    ]


def test_get_issues_exposes_scanned_range_when_nothing_is_found(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
) -> None:
    issues = get_issues(manager, last_seen_after=hours_ago(100))

    assert issues == []
    assert len(get_search_windows(script_session)) == 5
    assert manager.empty_scan_end == hours_ago(10)


def test_get_issues_does_not_advance_when_the_first_window_reaches_now(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
) -> None:
    issues = get_issues(manager, last_seen_after=hours_ago(3))

    assert issues == []
    assert get_search_windows(script_session) == [(hours_ago(3), hours_ago(0))]
    assert manager.empty_scan_end is None


def test_get_issues_limits_the_amount_of_probed_windows(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
) -> None:
    issues = get_issues(manager, last_seen_after=hours_ago(20_000))

    assert issues == []
    windows = get_search_windows(script_session)
    assert len(windows) == ASM_ISSUES_MAX_WINDOW_PROBES
    assert len(script_session.request_history) == ASM_ISSUES_MAX_WINDOW_PROBES
    scanned_hours = 186 + (ASM_ISSUES_MAX_WINDOW_PROBES - 5) * ASM_ISSUES_MAX_WINDOW_HOURS
    assert manager.empty_scan_end == hours_ago(20_000 - scanned_hours)
    assert windows[-1] == (
        hours_ago(20_000 - scanned_hours + ASM_ISSUES_MAX_WINDOW_HOURS),
        hours_ago(20_000 - scanned_hours),
    )


def test_get_issues_narrows_windows_holding_too_many_issues(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    issues_count: int = ASM_ISSUES_WINDOW_RESULTS_CEILING + 1
    google_threat_intelligence_product.add_asm_issues(
        [
            create_asm_issue(f"issue-{i}", last_seen=hours_ago(81.5))
            for i in range(issues_count)
        ]
    )

    issues = get_issues(manager, last_seen_after=hours_ago(100))

    assert len(issues) == LIMIT
    assert get_search_windows(script_session) == [
        (hours_ago(100), hours_ago(94)),
        (hours_ago(94), hours_ago(82)),
        (hours_ago(82), hours_ago(58)),
        (hours_ago(82), hours_ago(70)),
        (hours_ago(82), hours_ago(76)),
        (hours_ago(82), hours_ago(79)),
        (hours_ago(82), hours_ago(80.5)),
        (hours_ago(82), hours_ago(82 - ASM_ISSUES_MIN_WINDOW_HOURS)),
    ]
    pages: int = -(-issues_count // 100)
    assert len(script_session.request_history) == 8 + pages - 1
    assert manager.empty_scan_end == hours_ago(82)


def test_get_issues_narrows_the_initial_window_down_to_the_minimum(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    issues_count: int = ASM_ISSUES_WINDOW_RESULTS_CEILING + 1
    google_threat_intelligence_product.add_asm_issues(
        [
            create_asm_issue(f"issue-{i}", last_seen=hours_ago(9.5))
            for i in range(issues_count)
        ]
    )

    issues = get_issues(manager, last_seen_after=hours_ago(10))

    assert len(issues) == LIMIT
    assert get_search_windows(script_session) == [
        (hours_ago(10), hours_ago(4)),
        (hours_ago(10), hours_ago(7)),
        (hours_ago(10), hours_ago(8.5)),
        (hours_ago(10), hours_ago(10 - ASM_ISSUES_MIN_WINDOW_HOURS)),
    ]
    pages: int = -(-issues_count // 100)
    assert len(script_session.request_history) == 4 + pages - 1
    assert manager.empty_scan_end is None
    manager.logger.info.assert_any_call(
        f"Found {issues_count} issues in the window. Narrowing the window to 1 hours."
    )


def test_get_issues_skips_windows_holding_only_known_issues(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    google_threat_intelligence_product.add_asm_issues(
        [
            create_asm_issue("known-issue", last_seen=hours_ago(99)),
            create_asm_issue("new-issue", last_seen=hours_ago(90)),
        ]
    )

    issues = get_issues(manager, last_seen_after=hours_ago(100), existing_ids=["known-issue"])

    assert [issue.issue_id for issue in issues] == ["new-issue"]
    assert get_search_windows(script_session) == [
        (hours_ago(100), hours_ago(94)),
        (hours_ago(94), hours_ago(82)),
    ]
    assert manager.empty_scan_end == hours_ago(94)
    manager.logger.info.assert_any_call(
        "Issues in the window: 1 (already ingested: 1, filtered out by name: 0, new: 0)."
    )
    manager.logger.info.assert_any_call(
        f"No new issues were found between {hours_ago(100)} and {hours_ago(94)} "
        "(issues in window: 1)."
    )


def test_get_issues_collects_an_issue_repeated_across_pages_once(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    repeated_issue = create_asm_issue("repeated-issue", last_seen=hours_ago(9))
    google_threat_intelligence_product.add_asm_issues(
        [repeated_issue]
        + [create_asm_issue(f"issue-{i}", last_seen=hours_ago(8)) for i in range(100)]
        + [repeated_issue]
    )

    issues = get_issues(manager, last_seen_after=hours_ago(10))

    assert len(issues) == LIMIT
    assert [issue.issue_id for issue in issues].count("repeated-issue") == 1
    assert len(script_session.request_history) == 2
    manager.logger.info.assert_any_call(
        "Issues in the window: 102 (already ingested: 1, filtered out by name: 0, new: 101)."
    )
    manager.logger.info.assert_any_call(
        f"Returning the {LIMIT} earliest of the 101 new issues by last seen time."
    )


def test_get_issues_skips_windows_holding_only_filtered_out_issues(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    google_threat_intelligence_product.add_asm_issues(
        [
            create_asm_issue("blocked", last_seen=hours_ago(99), pretty_name="Open Port"),
            create_asm_issue("wanted", last_seen=hours_ago(90), pretty_name="Expired Cert"),
        ]
    )

    issues = get_issues(manager, last_seen_after=hours_ago(100), issue_name_filter={"!Open Port"})

    assert [issue.issue_id for issue in issues] == ["wanted"]
    assert len(get_search_windows(script_session)) == 2
    assert manager.empty_scan_end == hours_ago(94)
    manager.logger.info.assert_any_call(
        "Issues in the window: 1 (already ingested: 0, filtered out by name: 1, new: 0)."
    )


def test_get_issues_stops_walking_when_approaching_the_connector_timeout(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
) -> None:
    issues = get_issues(
        manager,
        last_seen_after=hours_ago(100),
        connector_starting_time=unix_now() - 1_000_000,
        python_process_timeout=180,
    )

    assert issues == []
    assert get_search_windows(script_session) == [(hours_ago(100), hours_ago(94))]
    assert manager.empty_scan_end == hours_ago(94)


def test_get_issues_keeps_walking_when_the_timeout_is_far(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
) -> None:
    get_issues(
        manager,
        last_seen_after=hours_ago(100),
        connector_starting_time=unix_now(),
        python_process_timeout=180,
    )

    assert len(get_search_windows(script_session)) == 5


def test_get_issues_raises_on_failed_search(
    manager: ApiManager,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    google_threat_intelligence_product.set_asm_search_error("Project not available")

    with pytest.raises(GoogleThreatIntelligenceExceptions, match="Project not available"):
        get_issues(manager, last_seen_after=hours_ago(100))

    assert manager.empty_scan_end is None


def test_get_issues_sends_project_id_header(
    manager: ApiManager,
    script_session: GoogleThreatIntelligenceSession,
) -> None:
    manager.project_id = "123456"

    get_issues(manager, last_seen_after=hours_ago(3))

    assert script_session.request_history[0].request.headers["PROJECT-ID"] == "123456"


def test_search_issues_by_page_keeps_hits_and_more_contract(
    manager: ApiManager,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    google_threat_intelligence_product.add_asm_issues(
        [create_asm_issue(f"issue-{i}", last_seen=hours_ago(1)) for i in range(101)]
    )

    hits, more = manager.search_issues_by_page(
        url=search_issues_url(hours_ago(2)),
        page_number=0,
        parser_method=parser.build_issue_objects,
    )

    assert len(hits) == 100
    assert more is True


def test_search_issues_by_page_logs_and_returns_empty_on_failed_search(
    manager: ApiManager,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    google_threat_intelligence_product.set_asm_search_error("boom")

    hits, more = manager.search_issues_by_page(
        url=search_issues_url(hours_ago(2)),
        page_number=0,
        parser_method=parser.build_issue_objects,
    )

    assert (hits, more) == ([], False)
    manager.logger.error.assert_called_once_with("Failed to fetch data - boom")


def test_window_constants_are_consistent() -> None:
    assert 0 < ASM_ISSUES_MIN_WINDOW_HOURS < ASM_ISSUES_INITIAL_WINDOW_HOURS
    assert ASM_ISSUES_INITIAL_WINDOW_HOURS < ASM_ISSUES_MAX_WINDOW_HOURS
    assert ASM_ISSUES_MAX_WINDOW_PROBES > 0
    assert ASM_ISSUES_WINDOW_RESULTS_CEILING >= 100

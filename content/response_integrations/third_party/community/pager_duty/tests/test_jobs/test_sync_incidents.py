from __future__ import annotations

from pager_duty.core.utils import clean_secops_comment, sanitize_case_comments
from pager_duty.tests.core.product import PagerDuty
from pager_duty.tests.core.session import PagerDutySession


def test_map_product_data_to_case_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_map,
) -> None:
    """Tests mapping product data to case successfully."""
    pagerduty.set_incidents({
        "incidents": [{"id": "P123", "status": "resolved", "incident_key": "key1"}]
    })

    job.map_product_data_to_case(job_case_map)

    assert len(script_session.request_history) == 2
    req_path_0 = script_session.request_history[0].request.url.path
    req_path_1 = script_session.request_history[1].request.url.path
    assert req_path_0.endswith("/incidents/P123")
    assert req_path_1.endswith("/incidents/P123/notes")
    assert "alert_1" in job_case_map.alert_metadata
    assert job_case_map.alert_metadata["alert_1"].status == "resolved"


def test_map_product_data_to_case_not_found_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_map,
) -> None:
    """Tests mapping product data to case when incident is not found."""
    job.map_product_data_to_case(job_case_map)

    assert len(script_session.request_history) == 1
    req_path = script_session.request_history[0].request.url.path
    assert req_path.endswith("/incidents/P123")
    assert "alert_1" not in job_case_map.alert_metadata


def test_sync_status_soar_to_pagerduty_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_sync,
) -> None:
    """Tests syncing status from SOAR to PagerDuty successfully."""
    pagerduty.set_incidents({
        "incidents": [{"id": "P123", "status": "triggered", "incident_key": "key1"}]
    })

    job.sync_status(job_case_sync)

    assert len(script_session.request_history) == 2
    req_path_0 = script_session.request_history[0].request.url.path
    req_path_1 = script_session.request_history[1].request.url.path
    assert req_path_0.endswith("/incidents/P123/notes")
    assert req_path_1.endswith("/incidents/P123")

    incident = pagerduty.get_incident("P123")
    assert incident["status"] == "resolved"


def test_sync_status_pagerduty_to_soar_close_case_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_sync_close_case,
) -> None:
    """Tests syncing status from PagerDuty to SOAR resulting in closing the alert."""
    job.sync_status(job_case_sync_close_case)

    assert job.soar_job.close_alert.called
    assert job._remove_synced_entries.called


def test_sync_status_pagerduty_to_soar_close_alert_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_sync_close_alert,
) -> None:
    """Tests syncing status from PagerDuty to SOAR (close alert)."""
    job.sync_status(job_case_sync_close_alert)

    assert job.soar_job.close_alert.called
    assert job._remove_synced_entries.called


def test_sync_status_soar_to_pagerduty_failure(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job_failing_api,
    job_case_sync,
) -> None:
    """Tests syncing status from SOAR to PagerDuty with API failure handling."""
    pagerduty.set_incidents({
        "incidents": [{"id": "P123", "status": "triggered", "incident_key": "key1"}]
    })

    job_failing_api.sync_status(job_case_sync)

    assert job_failing_api.logger.error.called


def test_sync_status_pagerduty_to_soar_close_alert_failure_retains_tracking(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job_failing_soar_close_alert,
    job_case_sync_close_alert,
) -> None:
    """Tests that close_alert failure does not remove the synced tracking entry."""
    job_failing_soar_close_alert.sync_status(job_case_sync_close_alert)

    assert not job_failing_soar_close_alert._remove_synced_entries.called
    assert job_failing_soar_close_alert.logger.error.called


def test_sync_comments_case_closed_skips(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_closed,
) -> None:
    """Tests that sync_comments skips when the case is already closed."""
    job.sync_comments(job_case_closed)

    assert not job.soar_job.add_comment.called


def test_sync_case_comments_to_product_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_sync,
) -> None:
    """Tests syncing SecOps comments to PagerDuty incident notes via session."""
    job.processed_items = {"1": ["P123"]}

    job.sync_case_comments_to_product(job_case_sync, ["SecOps investigation comment"])

    assert len(script_session.request_history) == 1
    req = script_session.request_history[0].request
    assert req.method.value == "POST"
    assert req.url.path.endswith("/incidents/P123/notes")


def test_sync_case_comments_to_product_failure(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job_failing_api,
    job_case_sync,
) -> None:
    """Tests handling failure when adding note to PagerDuty incident."""
    job_failing_api.processed_items = {"1": ["P123"]}

    job_failing_api.sync_case_comments_to_product(
        job_case_sync, ["SecOps investigation comment"]
    )

    assert job_failing_api.logger.error.called


def test_extract_product_id_from_ticket_id(job, ticket_with_id) -> None:
    """Tests extracting PagerDuty incident ID directly from non-UUID ticket_id."""
    extracted_id = job._extract_product_id_from_ticket(ticket_with_id)

    assert extracted_id == "P12345"


def test_extract_product_id_from_context_property(job, ticket_with_context) -> None:
    """Tests extracting PagerDuty ID from context when ticket_id is a UUID."""
    extracted_id = job._extract_product_id_from_ticket(ticket_with_context)

    assert extracted_id == "P99999"


def test_is_alert_and_product_closed(job, job_case_sync) -> None:
    """Tests checking if alert and product are both closed."""
    assert (
        job.is_alert_and_product_closed(
            job_case_sync, {"id": "P123", "status": "resolved"}
        )
        is True
    )

    assert (
        job.is_alert_and_product_closed(
            job_case_sync, {"id": "P123", "status": "triggered"}
        )
        is False
    )

    job_case_sync.case_detail.alerts[0].status = "open"
    assert (
        job.is_alert_and_product_closed(
            job_case_sync, {"id": "P123", "status": "resolved"}
        )
        is False
    )


def test_clean_secops_comment_special_characters() -> None:
    """Tests cleaning special characters, mentions, and HTML entities."""
    raw = '!<@>@</@>#$%^&amp;*()_+} {}|":&gt;?&lt;&lt;&lt;'
    cleaned = clean_secops_comment(raw)
    assert cleaned == '!@#$%^&*()_+} {}|":>?<<<'


def test_clean_secops_comment_mentions_and_html_tags() -> None:
    """Tests cleaning various mentions, HTML tags, breaks, and entities."""
    raw = (
        "<p>Hello <@>john</@> &amp; <@>@sarah</@>!</p>"
        '<p>Check &lt;code&gt; &amp; &quot;quotes&quot;</p>'
    )
    cleaned = clean_secops_comment(raw)
    assert cleaned == 'Hello @john & @sarah!\nCheck <code> & "quotes"'

    assert (
        clean_secops_comment("Line 1<br>Line 2<br/>Line 3")
        == "Line 1\nLine 2\nLine 3"
    )
    assert clean_secops_comment("") == ""


def test_clean_secops_comment_urls_and_rich_styling() -> None:
    """Tests cleaning URLs with query parameters and rich text styles."""
    url_raw = (
        '<p>Check <a href="https://example.com/api?user=admin&amp;'
        'tag=&lt;threat&gt;">https://example.com/api?user=admin&amp;'
        "tag=&lt;threat&gt;</a></p>"
    )
    assert (
        clean_secops_comment(url_raw)
        == "Check https://example.com/api?user=admin&tag=<threat>"
    )

    rich_raw = (
        "<p><strong>Critical:</strong> <em>Malicious payload</em> in "
        "<code>C:\\Windows\\System32\\</code>. "
        "Please <del>ignore</del> <u>check now</u>!</p>"
    )
    assert (
        clean_secops_comment(rich_raw)
        == "Critical: Malicious payload in C:\\Windows\\System32\\. "
        "Please ignore check now!"
    )

    complex_raw = (
        "<p>Alert: CPU &gt;= 95% &amp; memory leak! "
        "Contact <@>soc-lead</@> on-call.<br>"
        'Run: <code>curl -H "Auth: Bearer &lt;key&gt;"</code></p>'
    )
    assert (
        clean_secops_comment(complex_raw)
        == "Alert: CPU >= 95% & memory leak! Contact @soc-lead on-call.\n"
        'Run: curl -H "Auth: Bearer <key>"'
    )


def test_sanitize_case_comments(job_case_with_rich_comments) -> None:
    """Tests sanitizing case comments in JobCase."""
    sanitize_case_comments(job_case_with_rich_comments)
    assert (
        job_case_with_rich_comments.case_comments[0]["comment"]
        == '!@#$%^&*()_+} {}|":>?<<<'
    )
    assert (
        job_case_with_rich_comments.case_comments[1]["comment"]
        == "Another <clean> comment"
    )


def test_sync_comments_special_characters_soar_to_pagerduty(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job_comments_sync,
    job_case_sync_comments,
) -> None:
    """Tests that rich-text comments are sanitized and synced to PagerDuty."""
    job_comments_sync.sync_comments(job_case_sync_comments)

    assert len(script_session.request_history) == 1
    resp = script_session.request_history[0].response
    assert (
        resp.json()["note"]["content"]
        == 'Google SecOps 1: !@#$%^&*()_+} {}|":>?<<<'
    )


def test_sync_case_status_to_product_cleans_closure_comment(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job_with_closure_comment,
    job_case_sync,
) -> None:
    """Tests that rich-text closure comments are sanitized in PagerDuty."""
    pagerduty.set_incidents({
        "incidents": [{"id": "P123", "status": "triggered", "incident_key": "key1"}]
    })

    job_with_closure_comment._sync_case_status_to_product(
        job_case_sync.get_status_to_sync(), job_case_sync
    )

    assert len(script_session.request_history) == 2
    note_resp = script_session.request_history[0].response
    assert note_resp.json()["note"]["content"] == "Issue resolved with & <system fix>"

from __future__ import annotations

from typing import Any, Optional


def cyber_alert(
    identifier: str,
    detection_ids: list,
    creation_time: int = 1000,
    device_product: str = "Vectra RUX",
    investigation_status: Optional[str] = None,
) -> dict:
    """Build a single `cyber_alerts` entry as returned by `_get_case_by_id`.

    Mirrors the shape UtilsManager's job helpers (`get_case_alerts_by_detection_id`,
    `get_case_detection_alerts`) read: `additional_properties.DeviceProduct`/
    `investigation_status`, and one `security_events` entry per detection_id.
    """
    additional_properties: dict[str, Any] = {"DeviceProduct": device_product}
    if investigation_status is not None:
        additional_properties["investigation_status"] = investigation_status

    return {
        "identifier": identifier,
        "creation_time": creation_time,
        "additional_properties": additional_properties,
        "security_events": [
            {"additional_properties": {"detection_id": detection_id}}
            for detection_id in detection_ids
        ],
    }


def soar_case(
    cyber_alerts: list,
    environment: str = "Default Environment",
    modification_time: int = 1000,
    title: str = "",
    identifier: Optional[str] = None,
    status: int = 1,
) -> dict:
    """Build a case object as returned by `_get_case_by_id`.

    `title` is the CASE's own "title" field, which
    `UtilsManager.get_case_detection_alerts` carries onto each alert entry as
    "name" - it's how `_expand_terminal_detections_to_related_cases` finds a
    detection's other cases by name once its latest alert looks terminal.

    `identifier`/`status` are only needed when this case is returned from
    `get_cases_by_filter` (i.e. stashed in a test's
    `job._historical_cases_by_name`, see tests/test_jobs/conftest.py) rather
    than fetched directly by ID - `get_open_cases_by_case_name` reads both
    straight off the case dict without a further `_get_case_by_id` call.
    Omitted for in-window cases (looked up by ID, so redundant there).
    """
    case = {
        "environment": environment,
        "modification_time": modification_time,
        "cyber_alerts": cyber_alerts,
        "title": title,
    }
    if identifier is not None:
        case["identifier"] = identifier
        case["status"] = status
    return case

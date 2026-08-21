from __future__ import annotations

import dataclasses
import json
import pathlib
from typing import Any, Optional

MOCKS_DIR = pathlib.Path(__file__).parent.parent / "mocks"
MOCK_RESPONSES_FILE = MOCKS_DIR / "mock_responses.json"
MOCK_DATA: dict[str, Any] = json.loads(MOCK_RESPONSES_FILE.read_text(encoding="utf-8"))


def mock(key: str) -> Any:
    """Fetch a named mock response, deep-copied so tests can mutate freely."""
    return json.loads(json.dumps(MOCK_DATA[key]))


def detection_event(**overrides: Any) -> dict:
    """Build a single events/detections record from the canned template.

    Starts from the first event in the "list_detection_events" mock and
    applies `overrides` on top, so tests can cheaply produce variants
    (e.g. a different `id`/`detection_id` pair, `triaged=True`) without
    repeating the full event payload.
    """
    event = mock("list_detection_events")["events"][0]
    event.update(overrides)
    return event


@dataclasses.dataclass
class VectraProduct:
    """Holds per-test overridable canned responses for the VectraRUX mock API.

    Every field defaults to `None`; when unset the mock session falls back
    to a sensible built-in default response so most tests only need to
    override the handful of fields relevant to the action under test.
    """

    token_response: Optional[dict] = None
    token_status_code: int = 200

    list_entities_response: Optional[list] = None
    describe_entity_response: Optional[list] = None
    list_detection_events_response: Optional[dict] = None
    list_detections_response: Optional[list] = None
    describe_detection_response: Optional[list] = None
    list_users_response: Optional[list] = None
    list_groups_response: Optional[list] = None
    assignment_response: Optional[dict] = None
    list_assignments_response: Optional[list] = None
    update_assignment_response: Optional[dict] = None
    add_note_response: Optional[dict] = None
    update_note_response: Optional[dict] = None
    list_entity_notes_response: Optional[list] = None
    remove_note_response: Optional[dict] = None
    list_tags_response: Optional[dict] = None
    update_tags_response: Optional[dict] = None
    set_entity_ticket_response: Optional[dict] = None
    set_detection_ticket_response: Optional[dict] = None
    set_entity_unresolved_priority_response: Optional[dict] = None
    set_detection_status_response: Optional[dict] = None
    close_detections_response: Optional[dict] = None
    open_detections_response: Optional[dict] = None
    query_investigation_response: Optional[dict] = None
    investigation_results_response: Optional[list] = None
    group_members_response: Optional[dict] = None
    group_update_response: Optional[dict] = None
    assign_entity_response: Optional[dict] = None
    specific_entity_info_response: Optional[dict] = None
    remove_assignment_status_code: int = 200
    remove_assignment_body: bytes = b"{}"
    download_pcap_status_code: int = 200
    download_pcap_content: bytes = b"PCAP-FILE-BYTES"
    download_pcap_filename: str = "detection.pcap"

    # Generic status-code / error injection, keyed by API name (see
    # constants.py's *_API_NAME values), so a single test can force any
    # given endpoint to fail without needing a dedicated field.
    status_overrides: dict = dataclasses.field(default_factory=dict)
    body_overrides: dict = dataclasses.field(default_factory=dict)

    def status_for(self, api_name: str, default: int = 200) -> int:
        return self.status_overrides.get(api_name, default)

    def body_for(self, api_name: str, default: Any) -> Any:
        return self.body_overrides.get(api_name, default)

    def fail(self, api_name: str, status_code: int, body: Any = None) -> None:
        """Convenience helper: make the given API name return an error."""
        self.status_overrides[api_name] = status_code
        if body is not None:
            self.body_overrides[api_name] = body

    def set_detection_events(
        self,
        events: list,
        next_checkpoint: Optional[int] = None,
        remaining_count: int = 0,
    ) -> None:
        """Convenience helper: set the events/detections response.

        Args:
            events (list): The `events` records to return, e.g. built with
                `tests.core.product.detection_event(**overrides)`.
            next_checkpoint (int, optional): The `next_checkpoint` cursor for
                the next page. Defaults to None (no more pages).
            remaining_count (int, optional): The `remaining_count` value.
                Defaults to 0.

        """
        self.list_detection_events_response = {
            "events": events,
            "next_checkpoint": next_checkpoint,
            "remaining_count": remaining_count,
        }

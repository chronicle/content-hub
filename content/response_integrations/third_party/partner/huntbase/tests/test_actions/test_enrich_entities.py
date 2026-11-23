from __future__ import annotations

from typing import TYPE_CHECKING

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from huntbase.actions import enrich_entities

from .. import common
from ..conftest import MockEntity

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from integration_testing.platform.script_output import MockActionOutput

    from ..core.product import Huntbase
    from ..core.session import HuntbaseSession

IP = MockEntity("203.0.113.10", "ADDRESS")
UNKNOWN_DOMAIN = MockEntity("quiet.example", "DOMAIN")
HOST = MockEntity("WS-0142", "HOSTNAME")
USER = MockEntity("ALICE", "USERUNIQNAME")
CVE = MockEntity("CVE-2026-0001", "CVE")


def _fresh(*entities: MockEntity) -> list[MockEntity]:
    return [MockEntity(e.identifier, e.entity_type) for e in entities]


ENTITIES = _fresh(IP, UNKNOWN_DOMAIN, HOST, USER, CVE)


@set_metadata(integration_config=common.CONFIG, entities=ENTITIES)
def test_enrich_mixed_entities(
    huntbase: Huntbase,
    script_session: HuntbaseSession,
    action_output: MockActionOutput,
    entity_calls: dict[str, MagicMock],
) -> None:
    huntbase.add_indicator("203.0.113.10", id="ind-1", effective_confidence=90)
    huntbase.entities = [
        {
            "id": "e-host",
            "type": "device",
            "tags": ["finance"],
            "attributes": {
                "name": "ws-0142",
                "title": "WS-0142",
                "first_seen": "2026-09-01T00:00:00Z",
                "summary": {"last_seen": "2026-11-21T10:00:00Z", "findings": 2, "hunts": [{"id": "h1"}]},
                "url": "https://huntbase.example.com/entities/e-host?org=o1&src=api",
            },
        },
        {"id": "e-user", "type": "user", "attributes": {"name": "alice"}},
    ]

    enrich_entities.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert results.result_value is True
    assert "Successfully enriched" in results.output_message
    assert "203.0.113.10" in results.output_message
    assert "Huntbase has no record of: quiet.example" in results.output_message
    paths = [r.request.url.path for r in script_session.request_history]
    assert paths.count("/api/v1/intel/lookup") == 1
    assert paths.count("/api/v1/entities/by-value") == 2
    entity_types = [
        dict(r.request.kwargs["params"]).get("entity_type")
        for r in script_session.request_history
        if r.request.url.path.endswith("/by-value")
    ]
    assert entity_types == ["device", "user"]

    ip, domain, host, user, cve = ENTITIES
    assert ip.additional_properties["HB_status"] == "known"
    assert ip.additional_properties["HB_tlp"] == "amber"
    assert ip.additional_properties["HB_link"].endswith("/intelligence/indicators/ind-1?src=google_secops")
    assert ip.is_suspicious is True
    assert domain.additional_properties["HB_status"] == "unknown"
    assert domain.is_suspicious is False
    assert host.additional_properties["HB_entity_id"] == "e-host"
    assert host.additional_properties["HB_tags"] == "finance"
    assert host.additional_properties["HB_findings"] == 2
    assert host.additional_properties["HB_hunts"] == 1
    assert host.additional_properties["HB_last_seen"] == "2026-11-21T10:00:00Z"
    assert host.additional_properties["HB_link"] == "https://huntbase.example.com/entities/e-host?org=o1&src=api"
    assert user.additional_properties["HB_entity_id"] == "e-user"
    assert cve.additional_properties == {}

    entity_calls["update_entities"].assert_called_once()
    assert entity_calls["add_entity_insight"].call_count == 3
    json_result = results.json_output.json_result
    assert [item["Entity"] for item in json_result] == ["203.0.113.10", "quiet.example", "WS-0142", "ALICE"]


@set_metadata(
    integration_config=common.CONFIG,
    entities=_fresh(UNKNOWN_DOMAIN),
    parameters={"Only Enrich Known Values": "true", "Create Insight": "false"},
)
def test_enrich_nothing_known(action_output: MockActionOutput, entity_calls: dict[str, MagicMock]) -> None:
    enrich_entities.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert results.result_value is False
    assert "None of the provided entities were found in Huntbase." in results.output_message
    entity_calls["add_entity_insight"].assert_not_called()


@set_metadata(integration_config=common.CONFIG, entities=_fresh(CVE))
def test_enrich_no_supported_entities(script_session: HuntbaseSession, action_output: MockActionOutput) -> None:
    enrich_entities.main()

    assert action_output.results.result_value is False
    assert "No supported entities found" in action_output.results.output_message
    assert script_session.request_history == []


@set_metadata(integration_config=common.CONFIG, entities=_fresh(IP))
def test_enrich_api_failure(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.fail("intel_lookup", 403, body={"detail": "API keys can't call this endpoint."})

    enrich_entities.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.FAILED
    assert "API keys can't call this endpoint." in results.output_message


@set_metadata(integration_config=common.CONFIG, entities=_fresh(HOST), parameters={"Suspicious Threshold": "150"})
def test_enrich_bad_threshold(action_output: MockActionOutput) -> None:
    enrich_entities.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "between 0 and 100" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG, entities=_fresh(HOST))
def test_enrich_entity_search_failure_is_partial(
    huntbase: Huntbase, action_output: MockActionOutput, entity_calls: dict[str, MagicMock]
) -> None:
    huntbase.fail("entity_by_value", 500, times=10)

    enrich_entities.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert results.result_value is False
    assert "Could not enrich: WS-0142" in results.output_message

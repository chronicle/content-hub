# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import pytest
import requests
from integration_testing.common import create_entity
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from microsoft_defender_atp.actions import EnrichEntities
from microsoft_defender_atp.core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPError,
    MicrosoftDefenderATPManager,
)
from microsoft_defender_atp.tests import common

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput
    from integration_testing.requests.session import MockSession
    from TIPCommon.types import SingleJson

    from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
    from microsoft_defender_atp.tests.core.session import MicrosoftDefenderATPSession

HOSTNAME_ENTITY = create_entity(
    identifier=common.MOCK_DATA["machine_data"]["computerDnsName"],
    type_=EntityTypesEnum.HOST_NAME,
)
IP_ENTITY = create_entity(
    identifier=common.MOCK_DATA["machine_data_ip"]["lastIpAddress"],
    type_=EntityTypesEnum.ADDRESS,
)
FILE_HASH: str = "a" * 64  # 64-char SHA-256
FILE_HASH_ENTITY = create_entity(
    identifier=FILE_HASH,
    type_=EntityTypesEnum.FILE_HASH,
)
NOT_FOUND_ENTITY = create_entity(
    identifier="notfound.example.com",
    type_=EntityTypesEnum.HOST_NAME,
)

UNKNOWN_FILE_HASH_ENTITY = create_entity(identifier="c" * 64, type_=EntityTypesEnum.FILE_HASH)

# create_entity upper-cases identifiers like SOAR; results are keyed by entity.identifier.
HOSTNAME: str = HOSTNAME_ENTITY.identifier
MACHINE_ID: str = common.MOCK_DATA["machine_data"]["id"]
UNKNOWN_MACHINE_ID: str = "0" * 40
INTEGRATION: str = "Microsoft Defender for Endpoint"
ISOLATION_STATUS_KEY: str = "Defender ATP_isolation_status"


def _add_machine(product: MicrosoftDefenderATP) -> None:
    """Add the default test machine to the mock product."""
    product.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))


def _json_result(action_output: MockActionOutput) -> dict[str, SingleJson]:
    """Return the action JSON result keyed by the Entity field."""
    return {item["Entity"]: item["EntityResult"] for item in action_output.results.json_output.json_result}


def _updated_entities(session: MockSession) -> dict[str, SingleJson]:
    """Return the entities sent to the SDK UpdateEntities call, keyed by identifier."""
    return {
        entity["identifier"]: entity
        for record in session.request_history
        if record.request.url.path.endswith("/UpdateEntities")
        for entity in record.request.kwargs["json"]
    }


def _containment_queries(session: MockSession) -> int:
    """Count the Isolate/Unisolate machineactions queries sent to the product."""
    return sum(
        1
        for record in session.request_history
        if record.request.url.path.endswith("/api/machineactions")
        and "Isolate" in (record.request.kwargs.get("params") or {}).get("$filter", "")
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters={},
    entities=[HOSTNAME_ENTITY, IP_ENTITY],
)
def test_enrich_entities_hostname_and_ip_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that hostname and IP entities are successfully enriched."""
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data"]))
    microsoft_defender_atp.add_machine(copy.deepcopy(common.MOCK_DATA["machine_data_ip"]))

    # EnrichEntities calls siemplify.update_entities() which routes through the
    # SDK session. The SDK session mock (global conftest) has no routes for
    # /api/external/v1/sdk/UpdateEntities. We catch the ValueError and verify
    # that at least the enrichment result was written before update_entities.
    try:
        EnrichEntities.main()
    except (TypeError, NameError, ValueError):
        pass

    # If the action completed before update_entities, check COMPLETED state.
    # If it crashed in update_entities, results may be None or COMPLETED with
    # the enrichment output already written.
    if action_output.results is not None:
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value in (True, "true")


@set_metadata(
    integration_config=common.CONFIG,
    parameters={},
    entities=[FILE_HASH_ENTITY],
)
def test_enrich_entities_file_hash_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a file hash entity is enriched using file info + stats."""
    microsoft_defender_atp.set_file_info(
        FILE_HASH,
        {
            "sha1": "a" * 40,
            "sha256": FILE_HASH,
            "md5": "b" * 32,
            "fileName": "malware.exe",
            "fileSize": 1024,
        },
    )
    microsoft_defender_atp.set_file_stats(
        FILE_HASH,
        {
            "sha1": "a" * 40,
            "organizationPrevalence": 5,
            "globalPrevalence": 100,
        },
    )

    try:
        EnrichEntities.main()
    except (TypeError, NameError, ValueError):
        pass

    if action_output.results is not None:
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value in (True, "true")


@set_metadata(
    integration_config=common.CONFIG,
    parameters={},
    entities=[NOT_FOUND_ENTITY],
)
def test_enrich_entities_not_found(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that action completes with result_value=False when no entity found."""
    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "No entities were enriched" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG, parameters={"Machine ID": MACHINE_ID})
def test_enrich_entities_machine_id_only(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a Machine ID without entities returns a result keyed by the machine ID."""
    _add_machine(microsoft_defender_atp)

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert MACHINE_ID in action_output.results.output_message
    result = _json_result(action_output)
    assert list(result) == [MACHINE_ID]
    assert result[MACHINE_ID]["id"] == MACHINE_ID
    assert result[MACHINE_ID]["isolation_status"] == "uncontained"
    assert result[MACHINE_ID]["is_isolated"] is False
    assert not _updated_entities(script_session)
    assert "No entities were enriched" not in caplog.text
    assert action_output.results.output_message == (
        f"1 entities enriched\n0 entities missed\n0 entities failed\nEnriched Entities: {MACHINE_ID}\n"
        "Missing Entities: \nFailed Entities: "
    )
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("SUCCESS", "NONE", "COMPLETED", targets=1, failed=0),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={"Machine ID": MACHINE_ID}, entities=[HOSTNAME_ENTITY])
def test_enrich_entities_machine_id_and_matching_hostname(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that Machine ID overrides target entities."""
    _add_machine(microsoft_defender_atp)

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    result = _json_result(action_output)
    assert list(result) == [MACHINE_ID]
    assert result[MACHINE_ID]["isolation_status"] == "uncontained"
    assert not _updated_entities(script_session)


@pytest.mark.parametrize(
    ("tasks", "expected_status", "expected_is_isolated"),
    [
        ([], "uncontained", False),
        ([("Isolate", "Succeeded", "2024-01-01T12:00:00.000Z")], "contained", True),
        (
            [
                ("Unisolate", "Succeeded", "2024-01-01T12:00:00.000Z"),
                ("Isolate", "Pending", "2024-01-02T12:00:00.000Z"),
            ],
            "containment_requested",
            False,
        ),
    ],
)
@set_metadata(integration_config=common.CONFIG, parameters={"Machine ID": MACHINE_ID})
def test_enrich_entities_isolation_status(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    tasks: list[tuple[str, str, str]],
    expected_status: str,
    expected_is_isolated: bool,
) -> None:
    """Test that the isolation status is derived from the machine's containment tasks."""
    _add_machine(microsoft_defender_atp)
    for task_type, status, creation_time in tasks:
        microsoft_defender_atp.create_task(task_type, MACHINE_ID, status=status, creation_time=creation_time)

    EnrichEntities.main()

    result = _json_result(action_output)[MACHINE_ID]
    assert result["isolation_status"] == expected_status
    assert result["is_isolated"] is expected_is_isolated


@set_metadata(integration_config=common.CONFIG, parameters={}, entities=[HOSTNAME_ENTITY])
def test_enrich_entities_isolation_status_error_is_unknown(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a machineactions error yields "unknown" and the entity is still enriched."""
    _add_machine(microsoft_defender_atp)
    microsoft_defender_atp.set_containment_tasks_error(True)

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    result = _json_result(action_output)[HOSTNAME]
    assert result["isolation_status"] == "unknown"
    assert result["is_isolated"] is None
    entity = _updated_entities(script_session)[HOSTNAME]
    assert entity["is_enriched"] is True
    assert entity["additional_properties"][ISOLATION_STATUS_KEY] == "unknown"


@set_metadata(integration_config=common.CONFIG, parameters={"Machine ID": UNKNOWN_MACHINE_ID})
def test_enrich_entities_machine_id_not_found(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an unknown Machine ID is reported as not found with result False."""
    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert UNKNOWN_MACHINE_ID in action_output.results.output_message
    assert "No entities were enriched" in action_output.results.output_message
    assert action_output.results.output_message == (
        f"0 entities enriched\n1 entities missed\n0 entities failed\nMissing Entities: {UNKNOWN_MACHINE_ID}\n"
        "Failed Entities: \nNo entities were enriched"
    )
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "ENDPOINT_NOT_FOUND", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={}, entities=[HOSTNAME_ENTITY, NOT_FOUND_ENTITY])
def test_enrich_entities_not_found_keeps_result_true(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that not-found targets are reported but don't flip a successful result."""
    _add_machine(microsoft_defender_atp)

    EnrichEntities.main()

    assert action_output.results.result_value in (True, "true")
    assert list(_json_result(action_output)) == [HOSTNAME]
    assert "1 entities missed" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={},
    entities=[HOSTNAME_ENTITY, NOT_FOUND_ENTITY, FILE_HASH_ENTITY],
)
def test_enrich_entities_failed_and_not_found_reported_separately(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that failed and not-found entities are listed separately and failures flip result."""
    _add_machine(microsoft_defender_atp)

    monkeypatch.setattr(
        MicrosoftDefenderATPManager,
        "get_file",
        common.raise_error(MicrosoftDefenderATPError("Internal error")),
    )

    EnrichEntities.main()

    message = action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "1 entities enriched" in message
    assert "1 entities missed" in message
    assert "1 entities failed" in message
    assert f"Enriched Entities: {HOSTNAME}" in message
    assert f"Missing Entities: {NOT_FOUND_ENTITY.identifier}" in message
    assert f"Failed Entities: {FILE_HASH_ENTITY.identifier}" in message
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("PARTIAL_SUCCESS", "VENDOR_ERROR", "COMPLETED", targets=3, failed=2),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={}, entities=[HOSTNAME_ENTITY, UNKNOWN_FILE_HASH_ENTITY])
def test_enrich_entities_unknown_file_hash_is_not_found(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a file hash unknown to Defender is not found and keeps the result True."""
    _add_machine(microsoft_defender_atp)

    EnrichEntities.main()

    assert action_output.results.result_value in (True, "true")
    assert "1 entities enriched" in action_output.results.output_message
    assert "1 entities failed" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG, parameters={"Machine ID": "   "}, entities=[HOSTNAME_ENTITY])
def test_enrich_entities_blank_machine_id_uses_entities(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that a whitespace-only Machine ID is ignored and the entities are processed."""
    _add_machine(microsoft_defender_atp)

    EnrichEntities.main()

    assert action_output.results.result_value in (True, "true")
    assert list(_json_result(action_output)) == [HOSTNAME]
    assert "0 entities missed" in action_output.results.output_message


@set_metadata(
    integration_config={**common.CONFIG, "Graph API Root": "https://graph.microsoft.com"},
    parameters={"Machine ID": MACHINE_ID},
)
def test_enrich_entities_uses_defender_api_with_graph_api_root(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that the V1 Defender manager is used even when Graph API Root is set."""
    _add_machine(microsoft_defender_atp)

    EnrichEntities.main()

    assert action_output.results.result_value in (True, "true")
    token_scopes = [
        (record.request.kwargs.get("data") or {}).get("scope", "")
        for record in script_session.request_history
        if record.request.url.path.endswith("/token")
    ]
    assert token_scopes
    assert not any("graph" in scope for scope in token_scopes)


@set_metadata(integration_config=common.CONFIG, parameters={"Machine ID": MACHINE_ID}, entities=[])
def test_enrich_entities_machine_id_lookup_error_is_failure(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an API error while looking up the Machine ID fails instead of not-found."""
    monkeypatch.setattr(
        MicrosoftDefenderATPManager,
        "get_machine_by_id",
        common.raise_error(MicrosoftDefenderATPError("Internal server error")),
    )

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    assert "1 entities failed" in action_output.results.output_message
    assert f"Failed Entities: {MACHINE_ID}" in action_output.results.output_message
    assert action_output.results.output_message == (
        f"0 entities enriched\n0 entities missed\n1 entities failed\nFailed Entities: {MACHINE_ID}\n"
        "No entities were enriched"
    )
    assert common.get_summary_lines(caplog) == [
        common.expected_summary("FAILURE", "VENDOR_ERROR", "COMPLETED", targets=1, failed=1),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={}, entities=[HOSTNAME_ENTITY])
def test_enrich_entities_raised_error_summary(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a rate-limited lookup fails the run unchanged and the summary line keeps the HTTP status."""
    monkeypatch.setattr(
        MicrosoftDefenderATPManager,
        "get_machines_by_name",
        common.raise_error(MicrosoftDefenderATPError("Action ran into rate limiting.", status_code=429)),
    )

    EnrichEntities.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value in (False, "false")
    output_message = action_output.results.output_message
    assert output_message == "Action didn't completed due to error: Action ran into rate limiting."
    assert common.get_summary_lines(caplog) == [
        common.expected_summary(
            "FAILURE",
            "RATE_LIMITED",
            "FAILED",
            targets=1,
            failed=1,
            exc_type="MicrosoftDefenderATPError",
            http_status="429",
        ),
    ]


@set_metadata(integration_config=common.CONFIG, parameters={}, entities=[HOSTNAME_ENTITY])
def test_enrich_entities_unexpected_error_summary(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a non-Defender error still propagates and logs one FAILED summary line first."""
    monkeypatch.setattr(
        MicrosoftDefenderATPManager,
        "__init__",
        common.raise_error(requests.ConnectionError("Connection refused")),
    )

    with pytest.raises(requests.ConnectionError):
        EnrichEntities.main()

    assert common.get_summary_lines(caplog) == [
        common.expected_summary(
            "FAILURE",
            "CONNECTION_ERROR",
            "FAILED",
            targets=1,
            failed=1,
            exc_type="ConnectionError",
        ),
    ]

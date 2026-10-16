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

import json
from typing import TYPE_CHECKING

from integration_testing.common import get_request_payload
from integration_testing.requests.response import MockResponse
from integration_testing.set_meta import set_metadata

from ...jobs import PullMappings, PushMappings
from ..common import CONFIG_PATH

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    import pytest
    from integration_testing.request import MockRequest
    from TIPCommon.types import SingleJson

    from ...core.definitions import File
    from ..core.session import GitSyncMockSession

DEFAULT_PARAMETERS: SingleJson = {
    "Repo URL": "https://github.com/example/repo.git",
    "Branch": "main",
    "Git Password/Token/SSH Key": "secret-token",
    "Siemplify Verify SSL": True,
    "Git Verify SSL": True,
    "Source": "Security Command Center",
    "Commit": "Pushing mappings",
    "Commit Author": "Test Author <test@example.com>",
}

GITSYNC_METADATA_BYTES: bytes = (
    b'{"system_version": "6.1.38.77", "settings": {"update_root_readme": false}}'
)


class _MockGit:
    """In-memory Git test double capturing pushed repository files."""

    files: dict[str, bytes]
    include_base_path: bool = False

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def get_file_contents_from_path(self, path: str) -> bytes:
        if path in self.files:
            return self.files[path]
        raise KeyError(f"File not found: {path}")

    def get_file_objects_from_path(self, path: str) -> list[File]:
        _ = path
        return []

    def update_objects(self, files: Iterable[File], base_path: str = "") -> None:
        prefix: str = f"{base_path}/" if (self.include_base_path and base_path) else ""
        for file_obj in files:
            self.files[f"{prefix}{file_obj.path}"] = file_obj.content

    def commit_and_push(self, message: str) -> None:
        _ = message

    def cleanup(self) -> None:
        pass


def _install_mock_git(monkeypatch: pytest.MonkeyPatch, *, include_base_path: bool = False) -> dict[str, bytes]:
    store: dict[str, bytes] = {"GitSync.json": GITSYNC_METADATA_BYTES}

    class _BoundMockGit(_MockGit):
        files = store

    _BoundMockGit.include_base_path = include_base_path
    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", _BoundMockGit)
    return store


def _make_record(
    record_id: int,
    source: str,
    product: str,
    event_name: str,
    example_fields: list[SingleJson] | None = None,
) -> SingleJson:
    return {
        "id": record_id,
        "source": source,
        "product": product,
        "eventName": event_name,
        "familyName": "Network",
        "familyId": 10,
        "exampleEventFields": example_fields if example_fields is not None else [],
    }


def _make_legacy_rule_response(rule_id: int, source: str, product: str, event_name: str | None) -> MockResponse:
    field_entry: SingleJson = {
        "creationTimeUnixTimeInMs": 100,
        "modificationTimeUnixTimeInMs": 100,
        "mappingRule": {
            "id": rule_id,
            "source": source,
            "product": product,
            "eventName": event_name,
            "creationTimeUnixTimeInMs": 100,
            "modificationTimeUnixTimeInMs": 100,
        },
    }
    return MockResponse(content={"familyFields": [field_entry], "systemFields": []}, status_code=200)


def _make_1p_rule_response(rule_id: int, source: str, product: str, event_name: str) -> MockResponse:
    rule_entry: SingleJson = {
        "id": rule_id,
        "source": source,
        "product": product,
        "eventName": event_name,
        "creationTimeUnixTimeInMs": 100,
        "modificationTimeUnixTimeInMs": 100,
    }
    return MockResponse(content={"mappingRules": [rule_entry]}, status_code=200)


def _bind_routes(
    sdk_session: GitSyncMockSession,
    method: str,
    overrides: dict[str, Callable[[MockRequest], MockResponse]],
) -> None:
    for route_pattern in list(sdk_session.routes[method].keys()):
        for substr, handler in overrides.items():
            if substr in route_pattern:
                sdk_session.routes[method][route_pattern] = handler
                break


def _make_add_rules_collector(installed_events: list[str]) -> Callable[[MockRequest], MockResponse]:
    def _handler(request: MockRequest) -> MockResponse:
        for field in get_request_payload(request):
            event_name: str | None = (field.get("mappingRule") or {}).get("eventName")
            if event_name:
                installed_events.append(event_name)
        return MockResponse(content={}, status_code=200)

    return _handler


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_mappings_legacy_api_concurrent_rules(
    monkeypatch: pytest.MonkeyPatch,
    sdk_session: GitSyncMockSession,
) -> None:
    """Verify PushMappings fetches and filters mapping rules concurrently over the Legacy API."""
    monkeypatch.setattr(
        "TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api",
        lambda: False,
    )
    page_0: list[SingleJson] = [_make_record(1, "Security Command Center", "SCC", "Event_A", [{"key": "val"}])]
    page_1: list[SingleJson] = [
        _make_record(2, "Security Command Center", "SCC", "Event_B", [{"key": "val2"}]),
        _make_record(3, "OtherIntegration", "Other", "Event_C"),
    ]

    def mock_get_records(request: MockRequest) -> MockResponse:
        req_page: int = get_request_payload(request).get("requestedPage", 0)
        objs: list[SingleJson] = page_0 if req_page == 0 else page_1
        return MockResponse(content={"objectsList": objs, "metadata": {"totalNumberOfPages": 2}}, status_code=200)

    def mock_get_rules(request: MockRequest) -> MockResponse:
        if get_request_payload(request).get("eventName") == "Event_A":
            return _make_legacy_rule_response(11, "Security Command Center", "SCC", "Event_A")
        return _make_legacy_rule_response(12, "DifferentSource", "Other", "Event_B")

    _bind_routes(
        sdk_session,
        "POST",
        {"GetOntologyStatusRecords": mock_get_records, "GetMappingRulesForSettings": mock_get_rules},
    )
    updated_files: dict[str, bytes] = _install_mock_git(monkeypatch)

    PushMappings.main()

    pushed_records: list[SingleJson] = json.loads(updated_files["Security Command Center_Records.json"].decode("utf-8"))
    pushed_rules: list[SingleJson] = json.loads(updated_files["Security Command Center_Rules.json"].decode("utf-8"))
    assert [r["eventName"] for r in pushed_records] == ["Event_A", "Event_B"]
    assert all(r["exampleEventFields"] == [] for r in pushed_records)
    assert len(pushed_rules) == 1
    assert pushed_rules[0]["familyFields"][0]["mappingRule"]["eventName"] == "Event_A"


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_mappings_chronicle_1p_api_concurrent_rules(
    monkeypatch: pytest.MonkeyPatch,
    sdk_session: GitSyncMockSession,
) -> None:
    """Verify PushMappings fetches and filters mapping rules concurrently over the 1P API."""
    monkeypatch.setattr(
        "TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api",
        lambda: True,
    )
    monkeypatch.setattr("git_sync.core.SiemplifyApiClient.platform_supports_1p_api", lambda: True)
    records_1p: list[SingleJson] = [
        _make_record(101, "Security Command Center", "SCC", "Event_1P_A", [{"key": "val"}]),
        _make_record(102, "Security Command Center", "SCC", "Event_1P_B", [{"key": "val2"}]),
    ]

    def mock_get_1p_records(_request: MockRequest) -> MockResponse:
        return MockResponse(content={"ontologyRecords": records_1p}, status_code=200)

    def mock_get_1p_rules(request: MockRequest) -> MockResponse:
        if "/101/mappingRules" in str(getattr(request, "url", "")):
            return _make_1p_rule_response(21, "Security Command Center", "SCC", "Event_1P_A")
        return _make_1p_rule_response(22, "UnrelatedSource", "Other", "Event_1P_B")

    _bind_routes(sdk_session, "GET", {"mappingRules": mock_get_1p_rules, "ontologyRecords": mock_get_1p_records})
    updated_files: dict[str, bytes] = _install_mock_git(monkeypatch)

    PushMappings.main()

    pushed_records: list[SingleJson] = json.loads(updated_files["Security Command Center_Records.json"].decode("utf-8"))
    pushed_rules: list[SingleJson] = json.loads(updated_files["Security Command Center_Rules.json"].decode("utf-8"))
    assert [r["eventName"] for r in pushed_records] == ["Event_1P_A", "Event_1P_B"]
    assert all(r["exampleEventFields"] == [] for r in pushed_records)
    assert len(pushed_rules) == 1
    assert pushed_rules[0]["mappingRules"][0]["eventName"] == "Event_1P_A"


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_and_pull_mappings_large_rules_chunking(
    monkeypatch: pytest.MonkeyPatch,
    sdk_session: GitSyncMockSession,
) -> None:
    """Verify large mapping rules are split into part files on push and reassembled on pull."""
    monkeypatch.setattr(
        "TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api",
        lambda: False,
    )
    monkeypatch.setattr("git_sync.core.definitions.MAX_MAPPING_RULES_FILE_SIZE_BYTES", 600)
    records: list[SingleJson] = [
        _make_record(index, "Security Command Center", "SCC", f"Event_{index}") for index in (1, 2, 3)
    ]
    installed_rule_events: list[str] = []

    def mock_get_records(_request: MockRequest) -> MockResponse:
        return MockResponse(content={"objectsList": records, "metadata": {"totalNumberOfPages": 1}}, status_code=200)

    def mock_get_rules(request: MockRequest) -> MockResponse:
        event_name: str | None = get_request_payload(request).get("eventName")
        return _make_legacy_rule_response(11, "Security Command Center", "SCC", event_name)

    _bind_routes(
        sdk_session,
        "POST",
        {
            "GetOntologyStatusRecords": mock_get_records,
            "GetMappingRulesForSettings": mock_get_rules,
            "AddOrUpdateMappingRules": _make_add_rules_collector(installed_rule_events),
        },
    )
    repo_files: dict[str, bytes] = _install_mock_git(monkeypatch, include_base_path=True)

    PushMappings.main()

    base_dir: str = "Ontology/Mappings/Security Command Center"
    expected_parts: tuple[str, ...] = (
        f"{base_dir}/Security Command Center_Rules.json",
        f"{base_dir}/Security Command Center_Rules_part_2.json",
        f"{base_dir}/Security Command Center_Rules_part_3.json",
    )
    assert f"{base_dir}/Security Command Center_Records.json" in repo_files
    assert f"{base_dir}/Security Command Center_Rules_part_4.json" not in repo_files
    assert all(key in repo_files and len(repo_files[key]) <= 600 for key in expected_parts)

    PullMappings.main()
    assert installed_rule_events == ["Event_1", "Event_2", "Event_3"]

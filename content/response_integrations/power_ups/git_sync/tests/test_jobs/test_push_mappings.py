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

import pytest
from integration_testing.common import get_request_payload
from integration_testing.requests.response import MockResponse
from integration_testing.set_meta import set_metadata

from ...jobs import PullMappings, PushMappings
from ..common import CONFIG_PATH
from ..core.session import GitSyncMockSession

DEFAULT_PARAMETERS = {
    "Repo URL": "https://github.com/example/repo.git",
    "Branch": "main",
    "Git Password/Token/SSH Key": "secret-token",
    "Siemplify Verify SSL": True,
    "Git Verify SSL": True,
    "Source": "Security Command Center",
    "Commit": "Pushing mappings",
    "Commit Author": "Test Author <test@example.com>",
}


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_mappings_legacy_api_concurrent_rules(
    monkeypatch: pytest.MonkeyPatch,
    sdk_session: GitSyncMockSession,
) -> None:
    """Verifies that PushMappings fetches multi-page ontology records and mapping rules
    concurrently over the Legacy API while preserving record order and source filtering.
    """
    monkeypatch.setattr(
        "TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api",
        lambda: False,
    )
    page_0_records = [
        {
            "id": 1,
            "source": "Security Command Center",
            "product": "SCC",
            "eventName": "Event_A",
            "familyName": "Network",
            "familyId": 10,
            "exampleEventFields": [{"key": "val"}],
        },
    ]
    page_1_records = [
        {
            "id": 2,
            "source": "Security Command Center",
            "product": "SCC",
            "eventName": "Event_B",
            "familyName": "Network",
            "familyId": 10,
            "exampleEventFields": [{"key": "val2"}],
        },
        {
            "id": 3,
            "source": "OtherIntegration",
            "product": "Other",
            "eventName": "Event_C",
            "familyName": "Network",
            "familyId": 10,
            "exampleEventFields": [],
        },
    ]

    def mock_get_ontology_records(request):
        payload = get_request_payload(request)
        req_page = payload.get("requestedPage", 0)
        objs = page_0_records if req_page == 0 else page_1_records
        return MockResponse(
            content={"objectsList": objs, "metadata": {"totalNumberOfPages": 2}},
            status_code=200,
        )

    def mock_get_mapping_rules(request):
        payload = get_request_payload(request)
        event_name = payload.get("eventName")
        if event_name == "Event_A":
            return MockResponse(
                content={
                    "familyFields": [
                        {
                            "creationTimeUnixTimeInMs": 100,
                            "modificationTimeUnixTimeInMs": 100,
                            "mappingRule": {
                                "id": 11,
                                "source": "Security Command Center",
                                "product": "SCC",
                                "eventName": "Event_A",
                                "creationTimeUnixTimeInMs": 100,
                                "modificationTimeUnixTimeInMs": 100,
                            },
                        },
                    ],
                    "systemFields": [],
                },
                status_code=200,
            )
        return MockResponse(
            content={
                "familyFields": [
                    {
                        "creationTimeUnixTimeInMs": 100,
                        "modificationTimeUnixTimeInMs": 100,
                        "mappingRule": {
                            "id": 12,
                            "source": "DifferentSource",
                            "product": "Other",
                            "eventName": "Event_B",
                            "creationTimeUnixTimeInMs": 100,
                            "modificationTimeUnixTimeInMs": 100,
                        },
                    },
                ],
                "systemFields": [],
            },
            status_code=200,
        )

    for route_pattern in list(sdk_session.routes["POST"].keys()):
        if "GetOntologyStatusRecords" in route_pattern:
            sdk_session.routes["POST"][route_pattern] = mock_get_ontology_records
        elif "GetMappingRulesForSettings" in route_pattern:
            sdk_session.routes["POST"][route_pattern] = mock_get_mapping_rules

    updated_files = {}

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path):
            if path == "GitSync.json":
                return b'{"system_version": "6.1.38.77", "settings": {"update_root_readme": false}}'
            raise KeyError(f"File not found: {path}")

        def get_file_objects_from_path(self, path):
            return []

        def update_objects(self, files, base_path=""):
            for f in files:
                updated_files[f.path] = f.content

        def commit_and_push(self, message):
            pass

        def cleanup(self):
            pass

    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", MockGit)

    # Act
    PushMappings.main()

    # Assert
    assert "Security Command Center_Records.json" in updated_files
    assert "Security Command Center_Rules.json" in updated_files

    pushed_records = json.loads(
        updated_files["Security Command Center_Records.json"].decode("utf-8"),
    )
    pushed_rules = json.loads(
        updated_files["Security Command Center_Rules.json"].decode("utf-8"),
    )

    assert len(pushed_records) == 2
    assert [r["eventName"] for r in pushed_records] == ["Event_A", "Event_B"]
    assert all(r["exampleEventFields"] == [] for r in pushed_records)
    assert len(pushed_rules) == 1
    assert pushed_rules[0]["familyFields"][0]["mappingRule"]["eventName"] == "Event_A"


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_mappings_chronicle_1p_api_concurrent_rules(
    monkeypatch: pytest.MonkeyPatch,
    sdk_session: GitSyncMockSession,
) -> None:
    """Verifies that PushMappings fetches ontology records and mapping rules concurrently
    over the Chronicle (1P) API while preserving record order and source filtering.
    """
    monkeypatch.setattr(
        "TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api",
        lambda: True,
    )
    monkeypatch.setattr(
        "git_sync.core.SiemplifyApiClient.platform_supports_1p_api",
        lambda: True,
    )
    records_1p = [
        {
            "id": 101,
            "source": "Security Command Center",
            "product": "SCC",
            "eventName": "Event_1P_A",
            "familyName": "Network",
            "familyId": 10,
            "exampleEventFields": [{"key": "val"}],
        },
        {
            "id": 102,
            "source": "Security Command Center",
            "product": "SCC",
            "eventName": "Event_1P_B",
            "familyName": "Network",
            "familyId": 10,
            "exampleEventFields": [{"key": "val2"}],
        },
    ]

    def mock_get_1p_ontology_records(_request):
        return MockResponse(
            content={"ontologyRecords": records_1p},
            status_code=200,
        )

    def mock_get_1p_mapping_rules(request):
        url = str(getattr(request, "url", ""))
        if "/101/mappingRules" in url:
            return MockResponse(
                content={
                    "mappingRules": [
                        {
                            "id": 21,
                            "source": "Security Command Center",
                            "product": "SCC",
                            "eventName": "Event_1P_A",
                            "creationTimeUnixTimeInMs": 100,
                            "modificationTimeUnixTimeInMs": 100,
                        },
                    ],
                },
                status_code=200,
            )
        return MockResponse(
            content={
                "mappingRules": [
                    {
                        "id": 22,
                        "source": "UnrelatedSource",
                        "product": "Other",
                        "eventName": "Event_1P_B",
                        "creationTimeUnixTimeInMs": 100,
                        "modificationTimeUnixTimeInMs": 100,
                    },
                ],
            },
            status_code=200,
        )

    for route_pattern in list(sdk_session.routes["GET"].keys()):
        if "mappingRules" in route_pattern:
            sdk_session.routes["GET"][route_pattern] = mock_get_1p_mapping_rules
        elif "ontologyRecords" in route_pattern:
            sdk_session.routes["GET"][route_pattern] = mock_get_1p_ontology_records

    updated_files = {}

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path):
            if path == "GitSync.json":
                return b'{"system_version": "6.1.38.77", "settings": {"update_root_readme": false}}'
            raise KeyError(f"File not found: {path}")

        def get_file_objects_from_path(self, path):
            return []

        def update_objects(self, files, base_path=""):
            for f in files:
                updated_files[f.path] = f.content

        def commit_and_push(self, message):
            pass

        def cleanup(self):
            pass

    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", MockGit)

    # Act
    PushMappings.main()

    # Assert
    assert "Security Command Center_Records.json" in updated_files
    assert "Security Command Center_Rules.json" in updated_files

    pushed_records = json.loads(
        updated_files["Security Command Center_Records.json"].decode("utf-8"),
    )
    pushed_rules = json.loads(
        updated_files["Security Command Center_Rules.json"].decode("utf-8"),
    )

    assert len(pushed_records) == 2
    assert [r["eventName"] for r in pushed_records] == ["Event_1P_A", "Event_1P_B"]
    assert all(r["exampleEventFields"] == [] for r in pushed_records)
    assert len(pushed_rules) == 1
    assert pushed_rules[0]["mappingRules"][0]["eventName"] == "Event_1P_A"


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_push_and_pull_mappings_large_rules_chunking(
    monkeypatch: pytest.MonkeyPatch,
    sdk_session: GitSyncMockSession,
) -> None:
    """Verifies that mapping rules exceeding MAX_MAPPING_RULES_FILE_SIZE_BYTES are split
    into multiple part files on push and reassembled in exact order on pull.
    """
    monkeypatch.setattr(
        "TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api",
        lambda: False,
    )
    monkeypatch.setattr(
        "git_sync.core.definitions.MAX_MAPPING_RULES_FILE_SIZE_BYTES",
        600,
    )

    records = [
        {
            "id": index,
            "source": "Security Command Center",
            "product": "SCC",
            "eventName": f"Event_{index}",
            "familyName": "Network",
            "familyId": 10,
            "exampleEventFields": [],
        }
        for index in (1, 2, 3)
    ]

    def mock_get_ontology_records(_request):
        return MockResponse(
            content={"objectsList": records, "metadata": {"totalNumberOfPages": 1}},
            status_code=200,
        )

    def mock_get_mapping_rules(request):
        payload = get_request_payload(request)
        event_name = payload.get("eventName")
        return MockResponse(
            content={
                "familyFields": [
                    {
                        "creationTimeUnixTimeInMs": 100,
                        "modificationTimeUnixTimeInMs": 100,
                        "mappingRule": {
                            "id": 11,
                            "source": "Security Command Center",
                            "product": "SCC",
                            "eventName": event_name,
                            "creationTimeUnixTimeInMs": 100,
                            "modificationTimeUnixTimeInMs": 100,
                        },
                    },
                ],
                "systemFields": [],
            },
            status_code=200,
        )

    installed_rule_events: list[str] = []

    def mock_add_mapping_rules(request):
        payload = get_request_payload(request)
        for field in payload:
            event_name = (field.get("mappingRule") or {}).get("eventName")
            if event_name:
                installed_rule_events.append(event_name)
        return MockResponse(content={}, status_code=200)

    for route_pattern in list(sdk_session.routes["POST"].keys()):
        if "GetOntologyStatusRecords" in route_pattern:
            sdk_session.routes["POST"][route_pattern] = mock_get_ontology_records
        elif "GetMappingRulesForSettings" in route_pattern:
            sdk_session.routes["POST"][route_pattern] = mock_get_mapping_rules
        elif "AddOrUpdateMappingRules" in route_pattern:
            sdk_session.routes["POST"][route_pattern] = mock_add_mapping_rules

    repo_files: dict[str, bytes] = {
        "GitSync.json": (
            b'{"system_version": "6.1.38.77", '
            b'"settings": {"update_root_readme": false}}'
        ),
    }

    class MockGit:
        def __init__(self, *args, **kwargs):
            pass

        def get_file_contents_from_path(self, path: str) -> bytes:
            if path in repo_files:
                return repo_files[path]
            raise KeyError(f"File not found: {path}")

        def get_file_objects_from_path(self, path: str):
            return []

        def update_objects(self, files, base_path: str = ""):
            prefix = f"{base_path}/" if base_path else ""
            for file_obj in files:
                repo_files[f"{prefix}{file_obj.path}"] = file_obj.content

        def commit_and_push(self, message: str):
            pass

        def cleanup(self):
            pass

    monkeypatch.setattr("git_sync.core.GitSyncManager.Git", MockGit)

    # Act 1: Push Mappings (should split 3 rules into _Rules.json, _Rules_part_2.json, _Rules_part_3.json)
    PushMappings.main()

    base_dir = "Ontology/Mappings/Security Command Center"
    assert f"{base_dir}/Security Command Center_Records.json" in repo_files
    assert f"{base_dir}/Security Command Center_Rules.json" in repo_files
    assert f"{base_dir}/Security Command Center_Rules_part_2.json" in repo_files
    assert f"{base_dir}/Security Command Center_Rules_part_3.json" in repo_files
    assert f"{base_dir}/Security Command Center_Rules_part_4.json" not in repo_files

    for key in (
        f"{base_dir}/Security Command Center_Rules.json",
        f"{base_dir}/Security Command Center_Rules_part_2.json",
        f"{base_dir}/Security Command Center_Rules_part_3.json",
    ):
        assert len(repo_files[key]) <= 600

    # Act 2: Pull Mappings (should reassemble all 3 parts in order and install them)
    PullMappings.main()

    assert installed_rule_events == ["Event_1", "Event_2", "Event_3"]

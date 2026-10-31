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
from unittest.mock import MagicMock, patch

from TIPCommon.types import ChronicleSOAR

from ...core.definitions import Workflow
from ...core.GitSyncManager import GitSyncManager, WorkflowInstaller
from ..common import MOCKS_PATH
from ..core.product import GitSyncProduct

with open(MOCKS_PATH / "mock_data.json", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)

GIT_PLAYBOOK_DATA = MOCK_DATA["git_playbook"]
LOCAL_PLAYBOOK_DATA = MOCK_DATA["local_playbook"]


def test_duplicate_step_names_matching_prevention() -> None:
    """Tests that if there are multiple steps with the exact same instance name (e.g., multiple
    containers named 'Parallel Actions 4'), they are matched to different, unique local steps
    rather than mapping to the same step, preventing structural collapse.
    """
    # Arrange
    git_workflow = Workflow(GIT_PLAYBOOK_DATA)

    git_sync_product = GitSyncProduct()
    git_sync_product.local_playbook = LOCAL_PLAYBOOK_DATA

    mock_cache = MagicMock()
    mock_cache.get.return_value = -1

    chronicle_soar = MagicMock(spec=ChronicleSOAR)
    installer = WorkflowInstaller(
        chronicle_soar=chronicle_soar,
        api=git_sync_product,
        logger=MagicMock(),
        mod_time_cache=mock_cache,
    )

    # Act
    installer.update_local_workflow(git_workflow)

    # Assert
    assert git_sync_product.saved_playbook is not None
    steps = git_sync_product.saved_playbook["steps"]
    step_1 = next(x for x in steps if x["identifier"] == "local_PA4_1")
    step_2 = next(x for x in steps if x["identifier"] == "local_PA4_2")

    # Assert that each step matched a DIFFERENT, UNIQUE local step ID using pytest asserts
    assert step_1["identifier"] != step_2["identifier"]
    assert {step_1["identifier"], step_2["identifier"]} == {
        "local_PA4_1",
        "local_PA4_2",
    }


def test_push_block_writes_to_playbooks_path() -> None:
    """Test that GitContentManager.push_block writes to Playbooks/ path."""
    from ...core.GitContentManager import PLAYBOOKS_PATH, GitContentManager

    mock_git = MagicMock()
    mock_git.get_file_contents_from_path.return_value = "{}"
    mock_api = MagicMock()
    content_mgr = GitContentManager(mock_git, mock_api)

    block_data = {
        "name": "TestBlock",
        "categoryName": "CustomCat",
        "playbookType": 1,
    }
    block = Workflow(block_data)

    content_mgr.push_block(block)

    mock_git.update_objects.assert_called_once()
    call_args, call_kwargs = mock_git.update_objects.call_args
    assert call_kwargs.get("base_path") == f"{PLAYBOOKS_PATH}/CustomCat/TestBlock"


def test_get_mapping_rule_single_argument() -> None:
    """Test get_mapping_rule extracts mappingRule dict from single argument."""
    from ...core.definitions import get_mapping_rule

    assert get_mapping_rule({"mappingRule": {"source": "TestSrc"}}) == {
        "source": "TestSrc"
    }
    assert get_mapping_rule({"source": "DirectSrc"}) == {"source": "DirectSrc"}


def test_metadata_readme_addons_isolation() -> None:
    """Test that Metadata instances do not share mutable nested dicts."""
    from ...core.definitions import Metadata

    m1 = Metadata()
    m2 = Metadata()

    m1.set_readme_addon("Integration", "TestIntegration", "Custom Readme")
    assert m1.get_readme_addon("Integration", "TestIntegration") == "Custom Readme"
    assert m2.get_readme_addon("Integration", "TestIntegration") is None


def test_integration_generate_readme_custom_filtering() -> None:
    """Test that non-custom integrations only include custom actions/jobs/connectors in README."""
    import io
    import zipfile

    from ...core.definitions import Integration

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-CommercialTest.def",
            json.dumps(
                {
                    "Identifier": "CommercialTest",
                    "Description": "desc",
                    "PythonVersion": "3.11",
                }
            ),
        )
        zf.writestr(
            "Actions/BuiltInAction.json",
            json.dumps(
                {
                    "Name": "BuiltIn",
                    "Description": "builtin",
                    "TimeoutSeconds": 60,
                    "IsCustom": False,
                }
            ),
        )
        zf.writestr(
            "Actions/LegacyCustomAction.json",
            json.dumps(
                {
                    "Name": "LegacyCustomAct",
                    "Description": "custom",
                    "TimeoutSeconds": 60,
                    "IsCustom": True,
                }
            ),
        )
        zf.writestr(
            "Actions/OnePlatformCustomAction.json",
            json.dumps(
                {
                    "Name": "OnePlatformCustomAct",
                    "Description": "custom 1p",
                    "TimeoutSeconds": 60,
                    "Custom": True,
                }
            ),
        )
    zip_buf.seek(0)

    integration = Integration(
        {"identifier": "CommercialTest", "isCustomIntegration": False},
        zip_buf,
    )
    integration.generate_readme()

    assert "LegacyCustomAct" in integration.readme
    assert "OnePlatformCustomAct" in integration.readme
    assert "BuiltIn" not in integration.readme


def test_1p_commercial_integration_pull_custom_ide_items() -> None:
    """Test pulling a commercial integration with custom IDE items on 1P.
    First installs from marketplace if not installed, then updates/adds custom IDE items.
    """
    import io
    import zipfile

    from ...core.definitions import Integration
    from ...core.GitSyncManager import GitSyncManager

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-VirusTotal.def",
            json.dumps({"Identifier": "VirusTotal", "Version": "1.0.0", "IsCustom": False}),
        )
        zf.writestr(
            "ActionsDefinitions/ExistingCustomAction.actiondef",
            json.dumps({"Name": "ExistingCustomAction", "Description": "desc"}),
        )
        zf.writestr(
            "ActionsScripts/ExistingCustomAction.py",
            "def main(): pass",
        )
        zf.writestr(
            "ActionsDefinitions/NewCustomAction.actiondef",
            json.dumps({"Name": "NewCustomAction", "Description": "new desc"}),
        )
        zf.writestr(
            "ActionsScripts/NewCustomAction.py",
            "def main(): pass",
        )
    zip_buf.seek(0)

    integration = Integration(
        {"identifier": "VirusTotal", "isCustomIntegration": False},
        zip_buf,
    )

    # Verify get_all_items() returns the custom items and does not return 0 items
    items = integration.get_all_items()
    assert len(items) == 2
    item_names = [x["name"] for x in items]
    assert "ExistingCustomAction" in item_names
    assert "NewCustomAction" in item_names

    mock_api = MagicMock()
    mock_api.get_store_data.return_value = [{"identifier": "VirusTotal", "version": "1.0.0"}]
    mock_api.get_ide_cards.return_value = [
        {
            "identifier": "VirusTotal",
            "cards": [
                {"id": 42, "name": "ExistingCustomAction", "type": 1},
            ],
        }
    ]

    mock_siemplify = MagicMock()
    manager = MagicMock(spec=GitSyncManager)
    manager._siemplify = mock_siemplify
    manager.api = mock_api
    manager.logger = MagicMock()
    manager._cache = {}
    manager._marketplace_integrations = [{"identifier": "VirusTotal", "version": "1.0.0"}]
    manager.get_installed_integration_version = MagicMock(return_value="0.0")
    manager.install_marketplace_integration = MagicMock(return_value=True)
    manager._is_commercial_integration = lambda ident: GitSyncManager._is_commercial_integration(manager, ident)
    manager._is_integration_installed = lambda ident: GitSyncManager._is_integration_installed(manager, ident)

    # Call install_integration
    GitSyncManager.install_integration(manager, integration)

    # Assert commercial integration was installed from marketplace first
    manager.install_marketplace_integration.assert_called_once_with("VirusTotal", fallback_version="1.0.0")

    # Assert get_ide_cards was called
    mock_api.get_ide_cards.assert_called_once_with("VirusTotal")

    # Assert update_ide_item was called for both items
    assert mock_api.update_ide_item.call_count == 2
    calls = mock_api.update_ide_item.call_args_list

    # Existing item should have id set to 42
    existing_call = next(c for c in calls if c[0][0]["name"] == "ExistingCustomAction")
    assert existing_call[0][0]["id"] == 42
    assert existing_call[0][0]["script"] == "def main(): pass"
    assert existing_call[0][0]["type"] == 1

    # New item should not have an id
    new_call = next(c for c in calls if c[0][0]["name"] == "NewCustomAction")
    assert new_call[0][0].get("id") is None
    assert new_call[0][0]["script"] == "def main(): pass"
    assert new_call[0][0]["type"] == 1


def test_1p_commercial_integration_push_custom_ide_items() -> None:
    """Test pushing a commercial integration with custom IDE items on 1P.
    Verifies that separate folders (ActionsDefinitions, ActionsScripts) are created
    even when integration_card does not contain 'cards' (as on 1P).
    """
    import io
    import zipfile

    from ...core.definitions import Integration

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-GoogleCloudStorage.def",
            json.dumps({"Identifier": "GoogleCloudStorage", "Version": "1.0.0", "IsCustom": False}),
        )
        zf.writestr(
            "Actions/Copy of Ping.json",
            json.dumps({"Name": "Copy of Ping", "Description": "custom ping", "IsCustom": True}),
        )
        zf.writestr(
            "Actions/Copy of Ping.py",
            "print('custom ping')",
        )
    zip_buf.seek(0)

    # In 1P, get_installed_integrations() does not return 'cards'
    integration = Integration(
        {"identifier": "GoogleCloudStorage", "isCustomIntegration": False},
        zip_buf,
    )

    mock_api = MagicMock()
    mock_api.get_ide_cards.return_value = [
        {
            "identifier": "GoogleCloudStorage",
            "cards": [
                {
                    "id": 696,
                    "name": "Copy of Ping",
                    "displayName": "Copy of Ping",
                    "type": 1,
                    "isCustom": True,
                }
            ],
        }
    ]
    mock_api.get_ide_item.return_value = {
        "Name": "Copy of Ping",
        "Description": "custom ping",
        "Parameters": [],
    }

    from ...core import definitions

    with patch.object(definitions, "platform_supports_1p_api", return_value=True):
        files = list(integration.iter_files(mock_api))
    file_paths = [f.path for f in files]

    assert "README.md" in file_paths
    assert "Integration-GoogleCloudStorage.def" in file_paths
    assert "ActionsDefinitions/Copy of Ping.actiondef" in file_paths
    assert "ActionsScripts/Copy of Ping.py" in file_paths

    action_script_file = next(f for f in files if f.path == "ActionsScripts/Copy of Ping.py")
    assert action_script_file.content == b"print('custom ping')"
    mock_api.get_ide_item.assert_called_once_with("integrations/GoogleCloudStorage/actions/696", 1)


def test_1p_commercial_integration_push_only_custom_items() -> None:
    """Test pushing commercial integration only yields custom items, NOT built-in commercial actions."""
    import io
    import zipfile

    from ...core.definitions import Integration

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-GoogleCloudStorage.def",
            json.dumps({"Identifier": "GoogleCloudStorage", "Version": "1.0.0", "IsCustom": False}),
        )
        zf.writestr(
            "Actions/Ping.actiondef",
            json.dumps({"Name": "Ping", "Description": "ping", "Custom": True}),
        )
        zf.writestr(
            "Actions/Ping.py",
            "print('ping')",
        )
        zf.writestr(
            "Actions/Copy of Ping.actiondef",
            json.dumps({"Name": "Copy of Ping", "Description": "custom ping", "Custom": True}),
        )
        zf.writestr(
            "Actions/Copy of Ping.py",
            "print('custom ping')",
        )
    zip_buf.seek(0)

    integration = Integration(
        {"identifier": "GoogleCloudStorage", "isCustomIntegration": False},
        zip_buf,
    )

    mock_api = MagicMock()
    # 1P get_ide_cards returns both custom and non-custom items
    mock_api.get_ide_cards.return_value = [
        {
            "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/480",
            "id": 480,
            "displayName": "Copy of Ping",
            "custom": True,
            "actionType": 1,
        },
        {
            "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/185",
            "id": 185,
            "displayName": "Ping",
            "custom": False,
            "actionType": 1,
        },
    ]

    files = list(integration.iter_files(mock_api))
    file_paths = [f.path for f in files]

    # Only custom action should be yielded
    assert "ActionsDefinitions/Copy of Ping.actiondef" in file_paths
    assert "ActionsScripts/Copy of Ping.py" in file_paths

    # Built-in commercial action should NOT be yielded
    assert "ActionsDefinitions/Ping.actiondef" not in file_paths
    assert "ActionsScripts/Ping.py" not in file_paths


def test_1p_commercial_integration_push_custom_ide_items_api_error_fallback() -> None:
    """Test pushing when get_ide_item throws an exception (e.g. JSONDecodeError).
    Verifies that it catches the error and falls back to actions in the zip without crashing.
    """
    import io
    import zipfile

    from ...core import definitions
    from ...core.definitions import Integration

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-GoogleCloudStorage.def",
            json.dumps({"Identifier": "GoogleCloudStorage", "Version": "1.0.0", "IsCustom": False}),
        )
        zf.writestr(
            "Actions/Copy of Ping.json",
            json.dumps({"Name": "Copy of Ping", "Description": "custom ping", "IsCustom": True}),
        )
        zf.writestr(
            "Actions/Copy of Ping.py",
            "print('custom ping')",
        )
    zip_buf.seek(0)

    integration = Integration(
        {"identifier": "GoogleCloudStorage", "isCustomIntegration": False},
        zip_buf,
    )

    mock_api = MagicMock()
    mock_api.get_ide_cards.return_value = [
        {
            "identifier": "GoogleCloudStorage",
            "cards": [
                {
                    "id": 696,
                    "name": "Copy of Ping",
                    "displayName": "Copy of Ping",
                    "type": 1,
                    "isCustom": True,
                }
            ],
        }
    ]
    mock_api.get_ide_item.side_effect = Exception("Failed to parse response as JSON.")

    with patch.object(definitions, "platform_supports_1p_api", return_value=True):
        files = list(integration.iter_files(mock_api))
    file_paths = [f.path for f in files]

    # Must still produce the custom files via fallback
    assert "ActionsDefinitions/Copy of Ping.actiondef" in file_paths
    assert "ActionsScripts/Copy of Ping.py" in file_paths


def test_1p_commercial_integration_push_readme_and_files_matches_pettler() -> None:
    """Test full push_integration for a 1P commercial integration like GoogleCloudStorage.
    Replicates exact Pettler captured traffic:
    - Multiple built-in actions (custom=False)
    - Built-in managers (custom=False)
    - One custom action: Copy of Ping (custom=True, actionType=1, name='projects/.../actions/480')
    Verifies that ONLY Copy of Ping is pushed and listed in README.md.
    """
    import io
    import zipfile

    from ...core.definitions import Integration
    from ...core.GitContentManager import GitContentManager

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-GoogleCloudStorage.def",
            json.dumps({"Identifier": "GoogleCloudStorage", "Version": "16.0", "IsCustom": False}),
        )
        zf.writestr(
            "Actions/Ping.actiondef",
            json.dumps({"Name": "Ping", "DisplayName": "Ping", "Custom": True}),
        )
        zf.writestr("Actions/Ping.py", "print('ping')")
        zf.writestr(
            "Actions/Download.actiondef",
            json.dumps({"Name": "Download an Object From a Bucket", "DisplayName": "Download an Object From a Bucket", "Custom": True}),
        )
        zf.writestr("Actions/Download.py", "print('download')")
        zf.writestr(
            "Actions/Copy of Ping.actiondef",
            json.dumps({"Name": "Copy of Ping", "DisplayName": "Copy of Ping", "Custom": True}),
        )
        zf.writestr("Actions/Copy of Ping.py", "print('copy of ping')")
    zip_buf.seek(0)

    mock_git = MagicMock()
    mock_git.get_file_contents_from_path.side_effect = KeyError
    mock_api = MagicMock()
    mock_api.get_ide_cards.return_value = [
        {
            "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/480",
            "id": 480,
            "displayName": "Copy of Ping",
            "custom": True,
            "actionType": 1,
        },
        {
            "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/185",
            "id": 185,
            "displayName": "Download an Object From a Bucket",
            "custom": False,
            "actionType": 1,
        },
        {
            "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/180",
            "id": 180,
            "displayName": "Ping",
            "custom": False,
            "actionType": 1,
        },
        {
            "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/managers/113",
            "id": 113,
            "displayName": "GoogleCloudStorageManager",
            "custom": False,
            "managerType": 4,
        },
    ]
    mock_api.get_ide_item.return_value = {
        "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/480",
        "displayName": "Copy of Ping",
        "custom": True,
        "script": "print('live ide script')",
    }

    content_manager = GitContentManager(git=mock_git, api=mock_api)
    integration = Integration(
        {"identifier": "GoogleCloudStorage", "custom": False},
        zip_buf,
    )

    content_manager.push_integration(integration)

    # Inspect files passed to git.update_objects
    assert mock_git.update_objects.called
    yielded_files = list(mock_git.update_objects.call_args[0][0])
    yielded_paths = [f.path for f in yielded_files]

    # Custom action must be present
    assert "ActionsDefinitions/Copy of Ping.actiondef" in yielded_paths
    assert "ActionsScripts/Copy of Ping.py" in yielded_paths

    # Built-in actions must NOT be present
    assert "ActionsDefinitions/Ping.actiondef" not in yielded_paths
    assert "ActionsScripts/Ping.py" not in yielded_paths
    assert "ActionsDefinitions/Download an Object From a Bucket.actiondef" not in yielded_paths
    assert "ActionsScripts/Download an Object From a Bucket.py" not in yielded_paths
    assert "Managers/GoogleCloudStorageManager.managerdef" not in yielded_paths

    # Check script content from live IDE item
    script_file = next(f for f in yielded_files if f.path == "ActionsScripts/Copy of Ping.py")
    assert script_file.content == b"print('live ide script')"

    # Check README.md
    readme_file = next(f for f in yielded_files if f.path == "README.md")
    assert b"Copy of Ping" in readme_file.content
    assert b"Download an Object From a Bucket" not in readme_file.content


def test_1p_commercial_integration_push_with_nested_cards_payload() -> None:
    """Test push_integration when get_ide_cards returns a 1P nested list:
    [{'identifier': 'GoogleCloudStorage', 'cards': [...]}]
    Verifies that the cards are unwrapped properly and the custom action is pushed.
    """
    import io
    import zipfile

    from ...core.definitions import Integration
    from ...core.GitContentManager import GitContentManager

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-GoogleCloudStorage.def",
            json.dumps({"Identifier": "GoogleCloudStorage", "Version": "16.0", "IsCustom": False}),
        )
    zip_buf.seek(0)

    mock_git = MagicMock()
    mock_git.get_file_contents_from_path.side_effect = KeyError
    mock_api = MagicMock()
    mock_api.get_ide_cards.return_value = [
        {
            "identifier": "GoogleCloudStorage",
            "cards": [
                {
                    "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/480",
                    "id": 480,
                    "displayName": "Copy of Ping",
                    "custom": True,
                    "actionType": 1,
                },
                {
                    "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/185",
                    "id": 185,
                    "displayName": "Ping",
                    "custom": False,
                    "actionType": 1,
                },
            ],
        }
    ]
    mock_api.get_ide_item.return_value = {
        "displayName": "Copy of Ping",
        "custom": True,
        "script": "print('live ide script')",
    }

    content_manager = GitContentManager(git=mock_git, api=mock_api)
    integration = Integration(
        {"identifier": "GoogleCloudStorage", "custom": False},
        zip_buf,
    )

    content_manager.push_integration(integration)

    assert mock_git.update_objects.called
    yielded_files = list(mock_git.update_objects.call_args[0][0])
    yielded_paths = [f.path for f in yielded_files]

    assert "ActionsDefinitions/Copy of Ping.actiondef" in yielded_paths
    assert "ActionsScripts/Copy of Ping.py" in yielded_paths
    assert "ActionsDefinitions/Ping.actiondef" not in yielded_paths


def test_1p_commercial_integration_pull_matches_and_updates_card() -> None:
    """Test pull/install_integration for a commercial integration with custom IDE item.
    Verifies that the custom action pulled from the repo matches the 1P IDE card
    using _determine_card_name and _determine_card_type, sets script['id'] = 480,
    and calls update_ide_item with the correct script content.
    """
    import io
    import zipfile

    from ...core.definitions import Integration
    from ...core.GitSyncManager import GitSyncManager

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-GoogleCloudStorage.def",
            json.dumps({"Identifier": "GoogleCloudStorage", "Version": "16.0", "IsCustom": False}),
        )
        zf.writestr(
            "ActionsDefinitions/Copy of Ping.actiondef",
            json.dumps({"name": "Copy of Ping", "displayName": "Copy of Ping", "type": 1, "custom": True}),
        )
        zf.writestr(
            "ActionsScripts/Copy of Ping.py",
            "print('updated ping script')",
        )
    zip_buf.seek(0)

    integration = Integration(
        {"identifier": "GoogleCloudStorage", "custom": False},
        zip_buf,
    )

    mock_api = MagicMock()
    mock_api.get_ide_cards.return_value = [
        {
            "identifier": "GoogleCloudStorage",
            "cards": [
                {
                    "name": "projects/project/locations/location/instances/instance/integrations/GoogleCloudStorage/actions/480",
                    "id": 480,
                    "displayName": "Copy of Ping",
                    "custom": True,
                    "actionType": 1,
                }
            ],
        }
    ]

    gitsync = GitSyncManager.__new__(GitSyncManager)
    gitsync.api = mock_api
    gitsync.logger = MagicMock()
    gitsync._is_integration_installed = MagicMock(return_value=True)
    gitsync.install_integration(integration)

    assert mock_api.update_ide_item.called
    updated_script = mock_api.update_ide_item.call_args[0][0]
    assert updated_script["name"] == "Copy of Ping"
    assert updated_script["id"] == 480
    assert updated_script["type"] == 1
    assert updated_script["integrationIdentifier"] == "GoogleCloudStorage"
    assert updated_script["script"] == "print('updated ping script')"


def test_custom_integration_pull_imports_as_package_even_if_in_marketplace() -> None:
    """Test that a custom integration (like CrowdStrikeFalcon customized locally)
    is imported as a whole zip package, and NOT installed from marketplace or
    patched per-item, even if the marketplace contains an integration with the same identifier.
    """
    import io
    import zipfile

    from ...core.definitions import Integration

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "Integration-CrowdStrikeFalcon.json",
            json.dumps({
                "Identifier": "CrowdStrikeFalcon",
                "Custom": True,
                "Version": "77",
                "Staging": "False",
            }),
        )
        zf.writestr("Actions/Get Alert.json", json.dumps({"Name": "Get Alert"}))
        zf.writestr("Actions/Get Alert.py", "print('alert')")
    zip_buf.seek(0)

    integration = Integration(
        {"identifier": "CrowdStrikeFalcon", "isCustomIntegration": True, "Staging": "False"},
        zip_buf,
    )
    assert integration.isCustom is True

    mock_api = MagicMock()
    gitsync = GitSyncManager.__new__(GitSyncManager)
    gitsync.api = mock_api
    gitsync.logger = MagicMock()
    gitsync._cache = {"marketplace": [{"identifier": "CrowdStrikeFalcon", "version": "1.0.0"}]}
    gitsync.install_marketplace_integration = MagicMock()

    gitsync.install_integration(integration)

    # Must call import_package
    assert mock_api.import_package.called
    call_args = mock_api.import_package.call_args[0]
    assert call_args[0] == "CrowdStrikeFalcon"

    # Must NOT call install_marketplace_integration
    gitsync.install_marketplace_integration.assert_not_called()

    # Must NOT call update_ide_item or get_ide_cards
    mock_api.get_ide_cards.assert_not_called()
    mock_api.update_ide_item.assert_not_called()


def test_git_content_manager_detects_custom_vs_commercial() -> None:
    """Test GitContentManager.get_integration properly detects custom vs commercial."""
    from ...core.GitContentManager import GitContentManager
    from ...core.GitManager import File

    content_mgr = GitContentManager.__new__(GitContentManager)
    mock_git = MagicMock()
    content_mgr.git = mock_git

    # Case 1: Custom integration with Integration-CrowdStrikeFalcon.json
    mock_git.get_file_objects_from_path.return_value = [
        File(
            "Integration-CrowdStrikeFalcon.json",
            json.dumps({"Identifier": "CrowdStrikeFalcon", "Custom": True, "Version": "77"}),
        ),
        File("Actions/Get Alert.json", "{}"),
    ]
    custom_integ = content_mgr.get_integration("CrowdStrikeFalcon")
    assert custom_integ is not None
    assert custom_integ.isCustom is True

    # Case 2: Commercial integration with Integration-GoogleCloudStorage.def
    mock_git.get_file_objects_from_path.return_value = [
        File(
            "Integration-GoogleCloudStorage.def",
            json.dumps({"Identifier": "GoogleCloudStorage", "Custom": False, "Version": "1.0.0"}),
        ),
        File("ActionsDefinitions/Ping.actiondef", "{}"),
    ]
    commercial_integ = content_mgr.get_integration("GoogleCloudStorage")
    assert commercial_integ is not None
    assert commercial_integ.isCustom is False



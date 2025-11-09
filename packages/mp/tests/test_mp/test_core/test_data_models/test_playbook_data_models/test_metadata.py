# Copyright 2025 Google LLC
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

import pytest
from mp.core.data_models.playbooks.playbook_meta.access_permissions import (
    AccessPermission,
    BuiltAccessPermission,
    NonBuiltAccessPermission,
    PlaybookAccessLevel,
)
from mp.core.data_models.playbooks.playbook_meta.metadata import (
    PlaybookMetadata,
    BuiltPlaybookMetadata,
    NonBuiltPlaybookMetadata,
    PlaybookCreationSource,
)
from mp.core.data_models.playbooks.playbook_meta.display_info import PlaybookType

BUILT_ACCESS_PERMISSION: BuiltAccessPermission = {
    "WorkflowOriginalIdentifier": "playbook_id",
    "User": "user",
    "AccessLevel": 1,
}

NON_BUILT_ACCESS_PERMISSION: NonBuiltAccessPermission = {
    "playbook_id": "playbook_id",
    "user": "user",
    "access_level": "VIEW",
}

ACCESS_PERMISSION = AccessPermission(
    playbook_id="playbook_id",
    user="user",
    access_level=PlaybookAccessLevel.VIEW,
)


class TestAccessPermissionDataModel:
    def test_from_built_with_valid_data(self):
        assert AccessPermission.from_built(BUILT_ACCESS_PERMISSION) == ACCESS_PERMISSION

    def test_from_non_built_with_valid_data(self):
        assert AccessPermission.from_non_built(NON_BUILT_ACCESS_PERMISSION) == ACCESS_PERMISSION

    def test_to_built(self):
        assert ACCESS_PERMISSION.to_built() == BUILT_ACCESS_PERMISSION

    def test_to_non_built(self):
        assert ACCESS_PERMISSION.to_non_built() == NON_BUILT_ACCESS_PERMISSION

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            AccessPermission.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            AccessPermission.from_non_built({})

    def test_from_built_to_built_is_idempotent(self):
        assert AccessPermission.from_built(BUILT_ACCESS_PERMISSION).to_built() == BUILT_ACCESS_PERMISSION

    def test_from_non_built_to_non_built_is_idempotent(self):
        assert AccessPermission.from_non_built(NON_BUILT_ACCESS_PERMISSION).to_non_built() == NON_BUILT_ACCESS_PERMISSION


BUILT_PLAYBOOK_METADATA: BuiltPlaybookMetadata = {
    "Identifier": "identifier",
    "Name": "name",
    "IsEnable": True,
    "Version": 1.0,
    "Description": "description",
    "CreationSource": 0,
    "DefaultAccessLevel": 1,
    "SimulationClone": False,
    "DebugAlertIdentifier": "debug_alert_id",
    "DebugBaseAlertIdentifier": "debug_base_alert_id",
    "IsDebugMode": False,
    "PlaybookType": 0,
    "TemplateName": "template_name",
    "OriginalWorkflowIdentifier": "original_workflow_id",
    "VersionComment": "version_comment",
    "VersionCreator": "version_creator",
    "LastEditor": "last_editor",
    "Creator": "creator",
    "Priority": 0,
    "Category": 0,
    "IsAutomatic": False,
    "IsArchived": False,
    "Permissions": [BUILT_ACCESS_PERMISSION],
}

NON_BUILT_PLAYBOOK_METADATA: NonBuiltPlaybookMetadata = {
    "identifier": "identifier",
    "is_enable": True,
    "version": 1.0,
    "name": "name",
    "description": "description",
    "creation_source": "USER_OR_API_INITIATED",
    "default_access_level": "VIEW",
    "simulation_clone": False,
    "debug_alert_identifier": "debug_alert_id",
    "debug_base_alert_identifier": "debug_base_alert_id",
    "is_debug_mode": False,
    "type": "PLAYBOOK",
    "template_name": "template_name",
    "original_workflow_identifier": "original_workflow_id",
    "version_comment": "version_comment",
    "version_creator": "version_creator",
    "last_editor": "last_editor",
    "creator": "creator",
    "priority": 0,
    "category": 0,
    "is_automatic": False,
    "is_archived": False,
    "permissions": [NON_BUILT_ACCESS_PERMISSION],
}

PLAYBOOK_METADATA = PlaybookMetadata(
    identifier="identifier",
    is_enable=True,
    version=1.0,
    name="name",
    description="description",
    creation_source=PlaybookCreationSource.USER_OR_API_INITIATED,
    default_access_level=PlaybookAccessLevel.VIEW,
    simulation_clone=False,
    debug_alert_identifier="debug_alert_id",
    debug_base_alert_identifier="debug_base_alert_id",
    is_debug_mode=False,
    type_=PlaybookType.PLAYBOOK,
    template_name="template_name",
    original_workflow_identifier="original_workflow_id",
    version_comment="version_comment",
    version_creator="version_creator",
    last_editor="last_editor",
    creator="creator",
    priority=0,
    category=0,
    is_automatic=False,
    is_archived=False,
    permissions=[ACCESS_PERMISSION],
)

BUILT_PLAYBOOK_METADATA_WITH_NONE: BuiltPlaybookMetadata = {
    "Identifier": "identifier",
    "Name": "name",
    "IsEnable": True,
    "Version": 1.0,
    "Description": "description",
    "CreationSource": None,
    "DefaultAccessLevel": None,
    "SimulationClone": None,
    "DebugAlertIdentifier": None,
    "DebugBaseAlertIdentifier": None,
    "IsDebugMode": False,
    "PlaybookType": 0,
    "TemplateName": None,
    "OriginalWorkflowIdentifier": "original_workflow_id",
    "VersionComment": None,
    "VersionCreator": None,
    "LastEditor": None,
    "Creator": "creator",
    "Priority": 0,
    "Category": 0,
    "IsAutomatic": False,
    "IsArchived": False,
    "Permissions": [],
}

NON_BUILT_PLAYBOOK_METADATA_WITH_NONE: NonBuiltPlaybookMetadata = {
    "identifier": "identifier",
    "is_enable": True,
    "version": 1.0,
    "name": "name",
    "description": "description",
    "creation_source": None,
    "default_access_level": None,
    "simulation_clone": None,
    "debug_alert_identifier": None,
    "debug_base_alert_identifier": None,
    "is_debug_mode": False,
    "type": "PLAYBOOK",
    "template_name": None,
    "original_workflow_identifier": "original_workflow_id",
    "version_comment": None,
    "version_creator": None,
    "last_editor": None,
    "creator": "creator",
    "priority": 0,
    "category": 0,
    "is_automatic": False,
    "is_archived": False,
    "permissions": [],
}

PLAYBOOK_METADATA_WITH_NONE = PlaybookMetadata(
    identifier="identifier",
    is_enable=True,
    version=1.0,
    name="name",
    description="description",
    creation_source=None,
    default_access_level=None,
    simulation_clone=None,
    debug_alert_identifier=None,
    debug_base_alert_identifier=None,
    is_debug_mode=False,
    type_=PlaybookType.PLAYBOOK,
    template_name=None,
    original_workflow_identifier="original_workflow_id",
    version_comment=None,
    version_creator=None,
    last_editor=None,
    creator="creator",
    priority=0,
    category=0,
    is_automatic=False,
    is_archived=False,
    permissions=[],
)


class TestPlaybookMetadataDataModel:
    def test_from_built_with_valid_data(self):
        assert PlaybookMetadata.from_built("", BUILT_PLAYBOOK_METADATA) == PLAYBOOK_METADATA

    def test_from_non_built_with_valid_data(self):
        assert PlaybookMetadata.from_non_built("", NON_BUILT_PLAYBOOK_METADATA) == PLAYBOOK_METADATA

    def test_to_built(self):
        assert PLAYBOOK_METADATA.to_built() == BUILT_PLAYBOOK_METADATA

    def test_to_non_built(self):
        assert PLAYBOOK_METADATA.to_non_built() == NON_BUILT_PLAYBOOK_METADATA

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            PlaybookMetadata.from_built("", {})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            PlaybookMetadata.from_non_built("", {})

    def test_from_built_with_none_values(self):
        assert PlaybookMetadata.from_built("", BUILT_PLAYBOOK_METADATA_WITH_NONE) == PLAYBOOK_METADATA_WITH_NONE

    def test_from_non_built_with_none_values(self):
        assert PlaybookMetadata.from_non_built("", NON_BUILT_PLAYBOOK_METADATA_WITH_NONE) == PLAYBOOK_METADATA_WITH_NONE

    def test_to_built_with_none_values(self):
        assert PLAYBOOK_METADATA_WITH_NONE.to_built() == BUILT_PLAYBOOK_METADATA_WITH_NONE

    def test_to_non_built_with_none_values(self):
        assert PLAYBOOK_METADATA_WITH_NONE.to_non_built() == NON_BUILT_PLAYBOOK_METADATA_WITH_NONE

    def test_from_built_to_built_is_idempotent(self):
        assert PlaybookMetadata.from_built("", BUILT_PLAYBOOK_METADATA).to_built() == BUILT_PLAYBOOK_METADATA

    def test_from_non_built_to_non_built_is_idempotent(self):
        assert PlaybookMetadata.from_non_built("", NON_BUILT_PLAYBOOK_METADATA).to_non_built() == NON_BUILT_PLAYBOOK_METADATA

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

from mp.core.data_models.playbooks.step.step_parameter import (
    StepParameter,
    BuiltStepParameter,
    NonBuiltStepParameter,
)
from mp.core.data_models.playbooks.step.step_debug_enrichment_data import (
    DebugStepEnrichmentData,
    BuiltStepDebugEnrichmentData,
    NonBuiltStepDebugEnrichmentData,
)
from mp.core.data_models.playbooks.step.step_debug_data import (
    StepDebugData,
    BuiltStepDebugData,
    NonBuiltStepDebugData,
)
from mp.core.data_models.playbooks.step.metadata import Step, BuiltStep, NonBuiltStep, StepType
from mp.core.data_models.playbooks.overview.metadata import (
    Overview,
    BuiltOverview,
    NonBuiltOverview,
    OverviewType,
)
from mp.core.data_models.playbooks.trigger.metadata import (
    Trigger,
    BuiltTrigger,
    NonBuiltTrigger,
    TriggerType,
)
from mp.core.data_models.condition.condition_group import (
    ConditionGroup,
    BuiltConditionGroup,
    NonBuiltConditionGroup,
    LogicalOperator,
)
from mp.core.data_models.condition.condition import (
    Condition,
    BuiltCondition,
    NonBuiltCondition,
    MatchType,
)
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


BUILT_STEP_DEBUG_ENRICHMENT_DATA: BuiltStepDebugEnrichmentData = {
    "Field": "field",
    "Value": "value",
    "UseInPlaybook": True,
    "IsCustom": False,
}

NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA: NonBuiltStepDebugEnrichmentData = {
    "field": "field",
    "value": "value",
    "use_in_playbook": True,
    "is_custom": False,
}

DEBUG_STEP_ENRICHMENT_DATA = DebugStepEnrichmentData(
    field="field",
    value="value",
    use_in_playbook=True,
    is_custom=False,
)

BUILT_STEP_DEBUG_DATA: BuiltStepDebugData = {
    "OriginalStepIdentifier": "step_id",
    "OriginalWorkflowIdentifier": "playbook_id",
    "ModificationTimeUnixTimeInMs": 1234567890,
    "CreationTimeUnixTimeInMs": 1234567890,
    "ResultValue": "result_value",
    "ResultJson": '{"key": "value"}',
    "ScopeEntitiesEnrichmentData": [BUILT_STEP_DEBUG_ENRICHMENT_DATA],
    "ScopeEntitiesEnrichmentDataJson": '[{"Field": "field", "Value": "value", "UseInPlaybook": true, "IsCustom": false}]',
    "TenantId": "tenant_id",
}

NON_BUILT_STEP_DEBUG_DATA: NonBuiltStepDebugData = {
    "step_id": "step_id",
    "playbook_id": "playbook_id",
    "creation_time": 1234567890,
    "modification_time": 1234567890,
    "result_value": "result_value",
    "result_json": '{"key": "value"}',
    "scope_entities_enrichment_data": [NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA],
    "tenant_id": "tenant_id",
}

STEP_DEBUG_DATA = StepDebugData(
    step_id="step_id",
    playbook_id="playbook_id",
    creation_time=1234567890,
    modification_time=1234567890,
    result_value="result_value",
    result_json='{"key": "value"}',
    scope_entities_enrichment_data=[DEBUG_STEP_ENRICHMENT_DATA],
    tenant_id="tenant_id",
)

BUILT_STEP_DEBUG_DATA_WITH_NONE: BuiltStepDebugData = {
    "OriginalStepIdentifier": "step_id",
    "OriginalWorkflowIdentifier": "playbook_id",
    "ModificationTimeUnixTimeInMs": 1234567890,
    "CreationTimeUnixTimeInMs": 1234567890,
    "ResultValue": "result_value",
    "ResultJson": '{"key": "value"}',
    "ScopeEntitiesEnrichmentData": [],
    "ScopeEntitiesEnrichmentDataJson": "[]",
    "TenantId": None,
}

NON_BUILT_STEP_DEBUG_DATA_WITH_NONE: NonBuiltStepDebugData = {
    "step_id": "step_id",
    "playbook_id": "playbook_id",
    "creation_time": 1234567890,
    "modification_time": 1234567890,
    "result_value": "result_value",
    "result_json": '{"key": "value"}',
    "scope_entities_enrichment_data": [],
    "tenant_id": None,
}

STEP_DEBUG_DATA_WITH_NONE = StepDebugData(
    step_id="step_id",
    playbook_id="playbook_id",
    creation_time=1234567890,
    modification_time=1234567890,
    result_value="result_value",
    result_json='{"key": "value"}',
    scope_entities_enrichment_data=[],
    tenant_id=None,
)

BUILT_STEP_PARAMETER: BuiltStepParameter = {
    "ParentStepIdentifier": "step_id",
    "ParentWorkflowIdentifier": "playbook_id",
    "Name": "name",
    "Value": "value",
}

NON_BUILT_STEP_PARAMETER: NonBuiltStepParameter = {
    "step_id": "step_id",
    "playbook_id": "playbook_id",
    "name": "name",
    "value": "value",
}

STEP_PARAMETER = StepParameter(
    step_id="step_id",
    playbook_id="playbook_id",
    name="name",
    value="value",
)

BUILT_STEP_PARAMETER_WITH_NONE: BuiltStepParameter = {
    "ParentStepIdentifier": "step_id",
    "ParentWorkflowIdentifier": "playbook_id",
    "Name": "name",
    "Value": None,
}

NON_BUILT_STEP_PARAMETER_WITH_NONE: NonBuiltStepParameter = {
    "step_id": "step_id",
    "playbook_id": "playbook_id",
    "name": "name",
    "value": None,
}

STEP_PARAMETER_WITH_NONE = StepParameter(
    step_id="step_id",
    playbook_id="playbook_id",
    name="name",
    value=None,
)

BUILT_STEP: BuiltStep = {
    "Name": "name",
    "Description": "description",
    "Identifier": "identifier",
    "OriginalStepIdentifier": "original_step_id",
    "ParentWorkflowIdentifier": "playbook_id",
    "ParentStepIdentifiers": ["parent_step_id"],
    "PreviousResultCondition": "previous_result_condition",
    "InstanceName": "instance_name",
    "IsAutomatic": True,
    "IsSkippable": True,
    "ActionProvider": "action_provider",
    "ActionName": "action_name",
    "Type": 0,
    "Integration": "integration",
    "Parameters": [BUILT_STEP_PARAMETER],
    "AutoSkipOnFailure": True,
    "IsDebugMockData": True,
    "StepDebugData": BUILT_STEP_DEBUG_DATA,
    "StartLoopStepIdentifier": "start_loop_step_id",
    "ParallelActions": [],
    "ParentContainerIdentifier": "parent_container_id",
    "IsTouchedByAi": True,
}

NON_BUILT_STEP: NonBuiltStep = {
    "name": "name",
    "description": "description",
    "identifier": "identifier",
    "original_step_id": "original_step_id",
    "playbook_id": "playbook_id",
    "parent_step_ids": ["parent_step_id"],
    "previous_result_condition": "previous_result_condition",
    "instance_name": "instance_name",
    "is_automatic": True,
    "is_skippable": True,
    "action_provider": "action_provider",
    "action_name": "action_name",
    "integration": "integration",
    "type": "ACTION",
    "parameters": [NON_BUILT_STEP_PARAMETER],
    "auto_skip_on_failure": True,
    "is_debug_mock_data": True,
    "step_debug_data": NON_BUILT_STEP_DEBUG_DATA,
    "start_loop_step_id": "start_loop_step_id",
    "parent_container_id": "parent_container_id",
    "is_touched_by_ai": True,
    "parallel_actions": [],
}

STEP = Step(
    name="name",
    description="description",
    identifier="identifier",
    original_step_id="original_step_id",
    playbook_id="playbook_id",
    parent_step_ids=["parent_step_id"],
    previous_result_condition="previous_result_condition",
    instance_name="instance_name",
    is_automatic=True,
    is_skippable=True,
    action_provider="action_provider",
    action_name="action_name",
    integration="integration",
    type_=StepType.ACTION,
    parameters=[STEP_PARAMETER],
    auto_skip_on_failure=True,
    is_debug_mock_data=True,
    is_touched_by_ai=True,
    step_debug_data=STEP_DEBUG_DATA,
    start_loop_step_id="start_loop_step_id",
    parent_container_id="parent_container_id",
    parallel_actions=[],
)

BUILT_STEP_WITH_NONE: BuiltStep = {
    "Name": "name",
    "Description": "description",
    "Identifier": "identifier",
    "OriginalStepIdentifier": "original_step_id",
    "ParentWorkflowIdentifier": "playbook_id",
    "ParentStepIdentifiers": [],
    "PreviousResultCondition": None,
    "InstanceName": "instance_name",
    "IsAutomatic": True,
    "IsSkippable": True,
    "ActionProvider": "action_provider",
    "ActionName": "action_name",
    "Type": 0,
    "Integration": "integration",
    "Parameters": [],
    "AutoSkipOnFailure": True,
    "IsDebugMockData": True,
    "StepDebugData": None,
    "StartLoopStepIdentifier": None,
    "ParallelActions": [],
    "ParentContainerIdentifier": None,
    "IsTouchedByAi": True,
}

NON_BUILT_STEP_WITH_NONE: NonBuiltStep = {
    "name": "name",
    "description": "description",
    "identifier": "identifier",
    "original_step_id": "original_step_id",
    "playbook_id": "playbook_id",
    "parent_step_ids": [],
    "previous_result_condition": None,
    "instance_name": "instance_name",
    "is_automatic": True,
    "is_skippable": True,
    "action_provider": "action_provider",
    "action_name": "action_name",
    "integration": "integration",
    "type": "ACTION",
    "parameters": [],
    "auto_skip_on_failure": True,
    "is_debug_mock_data": True,
    "step_debug_data": None,
    "start_loop_step_id": None,
    "parent_container_id": None,
    "is_touched_by_ai": True,
    "parallel_actions": [],
}

STEP_WITH_NONE = Step(
    name="name",
    description="description",
    identifier="identifier",
    original_step_id="original_step_id",
    playbook_id="playbook_id",
    parent_step_ids=[],
    previous_result_condition=None,
    instance_name="instance_name",
    is_automatic=True,
    is_skippable=True,
    action_provider="action_provider",
    action_name="action_name",
    integration="integration",
    type_=StepType.ACTION,
    parameters=[],
    auto_skip_on_failure=True,
    is_debug_mock_data=True,
    is_touched_by_ai=True,
    step_debug_data=None,
    start_loop_step_id=None,
    parent_container_id=None,
    parallel_actions=[],
)

BUILT_OVERVIEW: BuiltOverview = {
    "OverviewTemplate": {
        "Identifier": "identifier",
        "Name": "name",
        "Creator": "creator",
        "PlaybookDefinitionIdentifier": "playbook_id",
        "Type": 0,
        "AlertRuleType": "alert_rule_type",
        "Roles": [1, 2],
    },
    "Roles": ["role1", "role2"],
}

NON_BUILT_OVERVIEW: NonBuiltOverview = {
    "identifier": "identifier",
    "name": "name",
    "creator": "creator",
    "playbook_id": "playbook_id",
    "type": "PLAYBOOK_DEFAULT",
    "alert_rule_type": "alert_rule_type",
    "roles": [1, 2],
    "role_names": ["role1", "role2"],
}

OVERVIEW = Overview(
    identifier="identifier",
    name="name",
    creator="creator",
    playbook_id="playbook_id",
    type_=OverviewType.PLAYBOOK_DEFAULT,
    alert_rule_type="alert_rule_type",
    roles=[1, 2],
    role_names=["role1", "role2"],
)

BUILT_OVERVIEW_WITH_NONE: BuiltOverview = {
    "OverviewTemplate": {
        "Identifier": "identifier",
        "Name": "name",
        "Creator": None,
        "PlaybookDefinitionIdentifier": "playbook_id",
        "Type": 0,
        "AlertRuleType": None,
        "Roles": [],
    },
    "Roles": [],
}

NON_BUILT_OVERVIEW_WITH_NONE: NonBuiltOverview = {
    "identifier": "identifier",
    "name": "name",
    "creator": None,
    "playbook_id": "playbook_id",
    "type": "PLAYBOOK_DEFAULT",
    "alert_rule_type": None,
    "roles": [],
    "role_names": [],
}

OVERVIEW_WITH_NONE = Overview(
    identifier="identifier",
    name="name",
    creator=None,
    playbook_id="playbook_id",
    type_=OverviewType.PLAYBOOK_DEFAULT,
    alert_rule_type=None,
    roles=[],
    role_names=[],
)

BUILT_CONDITION: BuiltCondition = {
    "FieldName": "field_name",
    "Value": "value",
    "MatchType": 0,
}

NON_BUILT_CONDITION: NonBuiltCondition = {
    "field_name": "field_name",
    "value": "value",
    "match_type": "EQUAL",
}

CONDITION = Condition(
    field_name="field_name",
    value="value",
    match_type=MatchType.EQUAL,
)

BUILT_CONDITION_GROUP: BuiltConditionGroup = {
    "Conditions": [BUILT_CONDITION],
    "LogicalOperator": 0,
}

NON_BUILT_CONDITION_GROUP: NonBuiltConditionGroup = {
    "conditions": [NON_BUILT_CONDITION],
    "logical_operator": "AND",
}

CONDITION_GROUP = ConditionGroup(
    conditions=[CONDITION],
    logical_operator=LogicalOperator.AND,
)

BUILT_CONDITION_GROUP_WITH_NONE: BuiltConditionGroup = {
    "Conditions": [],
    "LogicalOperator": 0,
}

NON_BUILT_CONDITION_GROUP_WITH_NONE: NonBuiltConditionGroup = {
    "conditions": [],
    "logical_operator": "AND",
}

CONDITION_GROUP_WITH_NONE = ConditionGroup(
    conditions=[],
    logical_operator=LogicalOperator.AND,
)

BUILT_TRIGGER: BuiltTrigger = {
    "Identifier": "identifier",
    "IsEnabled": True,
    "DefinitionIdentifier": "playbook_id",
    "Type": 0,
    "LogicalOperator": 0,
    "Conditions": [BUILT_CONDITION],
    "Environments": ["env1", "env2"],
    "WorkflowName": "playbook_name",
}

NON_BUILT_TRIGGER: NonBuiltTrigger = {
    "identifier": "identifier",
    "is_enabled": True,
    "playbook_id": "playbook_id",
    "type_": "VENDOR_NAME",
    "conditions": [NON_BUILT_CONDITION],
    "logical_operator": "AND",
    "environments": ["env1", "env2"],
    "playbook_name": "playbook_name",
}

TRIGGER = Trigger(
    identifier="identifier",
    is_enabled=True,
    playbook_id="playbook_id",
    type_=TriggerType.VENDOR_NAME,
    conditions=[CONDITION],
    logical_operator=LogicalOperator.AND,
    environments=["env1", "env2"],
    playbook_name="playbook_name",
)

BUILT_TRIGGER_WITH_NONE: BuiltTrigger = {
    "Identifier": "identifier",
    "IsEnabled": True,
    "DefinitionIdentifier": "playbook_id",
    "Type": 0,
    "LogicalOperator": 0,
    "Conditions": [],
    "Environments": [],
    "WorkflowName": None,
}

NON_BUILT_TRIGGER_WITH_NONE: NonBuiltTrigger = {
    "identifier": "identifier",
    "is_enabled": True,
    "playbook_id": "playbook_id",
    "type_": "VENDOR_NAME",
    "conditions": [],
    "logical_operator": "AND",
    "environments": [],
    "playbook_name": None,
}

TRIGGER_WITH_NONE = Trigger(
    identifier="identifier",
    is_enabled=True,
    playbook_id="playbook_id",
    type_=TriggerType.VENDOR_NAME,
    conditions=[],
    logical_operator=LogicalOperator.AND,
    environments=[],
    playbook_name=None,
)

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

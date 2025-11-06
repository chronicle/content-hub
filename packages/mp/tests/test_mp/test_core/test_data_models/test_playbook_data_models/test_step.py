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
import json
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


class TestDebugStepEnrichmentDataModel:
    def test_from_built_with_valid_data(self):
        assert DebugStepEnrichmentData.from_built(BUILT_STEP_DEBUG_ENRICHMENT_DATA) == DEBUG_STEP_ENRICHMENT_DATA

    def test_from_non_built_with_valid_data(self):
        assert DebugStepEnrichmentData.from_non_built(NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA) == DEBUG_STEP_ENRICHMENT_DATA

    def test_to_built(self):
        assert DEBUG_STEP_ENRICHMENT_DATA.to_built() == BUILT_STEP_DEBUG_ENRICHMENT_DATA

    def test_to_non_built(self):
        assert DEBUG_STEP_ENRICHMENT_DATA.to_non_built() == NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            DebugStepEnrichmentData.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            DebugStepEnrichmentData.from_non_built({})


BUILT_STEP_DEBUG_DATA: BuiltStepDebugData = {
    "OriginalStepIdentifier": "step_id",
    "OriginalWorkflowIdentifier": "playbook_id",
    "ModificationTimeUnixTimeInMs": 1234567890,
    "CreationTimeUnixTimeInMs": 1234567890,
    "ResultValue": "result_value",
    "ResultJson": '''{"key": "value"}''',
    "ScopeEntitiesEnrichmentData": [BUILT_STEP_DEBUG_ENRICHMENT_DATA, BUILT_STEP_DEBUG_ENRICHMENT_DATA],
    "ScopeEntitiesEnrichmentDataJson": json.dumps([BUILT_STEP_DEBUG_ENRICHMENT_DATA, BUILT_STEP_DEBUG_ENRICHMENT_DATA]),
    "TenantId": None
}

NON_BUILT_STEP_DEBUG_DATA: NonBuiltStepDebugData = {
    "step_id": "step_id",
    "playbook_id": "playbook_id",
    "creation_time": 1234567890,
    "modification_time": 1234567890,
    "result_value": "result_value",
    "result_json": '''{"key": "value"}''',
    "scope_entities_enrichment_data": [NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA, NON_BUILT_STEP_DEBUG_ENRICHMENT_DATA],
}

STEP_DEBUG_DATA = StepDebugData(
    step_id="step_id",
    playbook_id="playbook_id",
    creation_time=1234567890,
    modification_time=1234567890,
    result_value="result_value",
    result_json='''{"key": "value"}''',
    scope_entities_enrichment_data=[DEBUG_STEP_ENRICHMENT_DATA, DEBUG_STEP_ENRICHMENT_DATA],
)


class TestStepDebugDataModel:
    def test_from_built_with_valid_data(self):
        assert StepDebugData.from_built(BUILT_STEP_DEBUG_DATA) == STEP_DEBUG_DATA

    def test_from_non_built_with_valid_data(self):
        assert StepDebugData.from_non_built(NON_BUILT_STEP_DEBUG_DATA) == STEP_DEBUG_DATA

    def test_to_built(self):
        assert STEP_DEBUG_DATA.to_built() == BUILT_STEP_DEBUG_DATA

    def test_to_non_built(self):
        assert STEP_DEBUG_DATA.to_non_built() == NON_BUILT_STEP_DEBUG_DATA

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            StepDebugData.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            StepDebugData.from_non_built({})


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


class TestStepParameterDataModel:
    def test_from_built_with_valid_data(self):
        assert StepParameter.from_built(BUILT_STEP_PARAMETER) == STEP_PARAMETER

    def test_from_non_built_with_valid_data(self):
        assert StepParameter.from_non_built(NON_BUILT_STEP_PARAMETER) == STEP_PARAMETER

    def test_to_built(self):
        assert STEP_PARAMETER.to_built() == BUILT_STEP_PARAMETER

    def test_to_non_built(self):
        assert STEP_PARAMETER.to_non_built() == NON_BUILT_STEP_PARAMETER

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            StepParameter.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            StepParameter.from_non_built({})


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
    "Parameters": [BUILT_STEP_PARAMETER, BUILT_STEP_PARAMETER],
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
    "parameters": [NON_BUILT_STEP_PARAMETER, NON_BUILT_STEP_PARAMETER],
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
    parameters=[STEP_PARAMETER, STEP_PARAMETER],
    auto_skip_on_failure=True,
    is_debug_mock_data=True,
    is_touched_by_ai=True,
    step_debug_data=STEP_DEBUG_DATA,
    start_loop_step_id="start_loop_step_id",
    parent_container_id="parent_container_id",
    parallel_actions=[],
)


class TestStepDataModel:
    def test_from_built_with_valid_data(self):
        assert Step._from_built("", BUILT_STEP) == STEP

    def test_from_non_built_with_valid_data(self):
        assert Step._from_non_built("", NON_BUILT_STEP) == STEP

    def test_to_built(self):
        assert STEP.to_built() == BUILT_STEP

    def test_to_non_built(self):
        assert STEP.to_non_built() == NON_BUILT_STEP

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            Step.from_built("", {})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            Step.from_non_built("", {})

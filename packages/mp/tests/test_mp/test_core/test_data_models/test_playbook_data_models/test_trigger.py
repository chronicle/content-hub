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
from mp.core.data_models.playbooks.trigger.metadata import (
    Trigger,
    BuiltTrigger,
    NonBuiltTrigger,
    TriggerType,
)
from mp.core.data_models.condition.condition_group import LogicalOperator
from mp.core.data_models.condition.condition import (
    Condition,
    BuiltCondition,
    NonBuiltCondition,
    MatchType,
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

BUILT_TRIGGER: BuiltTrigger = {
    "Identifier": "identifier",
    "IsEnabled": True,
    "DefinitionIdentifier": "playbook_id",
    "Type": 0,
    "LogicalOperator": 0,
    "Conditions": [BUILT_CONDITION, BUILT_CONDITION],
    "Environments": ["env1", "env2"],
    "WorkflowName": "playbook_name",
}

NON_BUILT_TRIGGER: NonBuiltTrigger = {
    "identifier": "identifier",
    "is_enabled": True,
    "playbook_id": "playbook_id",
    "type_": "VENDOR_NAME",
    "conditions": [NON_BUILT_CONDITION, NON_BUILT_CONDITION],
    "logical_operator": "AND",
    "environments": ["env1", "env2"],
    "playbook_name": "playbook_name",
}

TRIGGER = Trigger(
    identifier="identifier",
    is_enabled=True,
    playbook_id="playbook_id",
    type_=TriggerType.VENDOR_NAME,
    conditions=[CONDITION, CONDITION],
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


class TestTriggerDataModel:
    def test_from_built_with_valid_data(self):
        assert Trigger.from_built(BUILT_TRIGGER) == TRIGGER

    def test_from_non_built_with_valid_data(self):
        assert Trigger.from_non_built(NON_BUILT_TRIGGER) == TRIGGER

    def test_to_built(self):
        assert TRIGGER.to_built() == BUILT_TRIGGER

    def test_to_non_built(self):
        assert TRIGGER.to_non_built() == NON_BUILT_TRIGGER

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            Trigger.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            Trigger.from_non_built({})

    def test_from_built_with_none_values(self):
        assert Trigger.from_built(BUILT_TRIGGER_WITH_NONE) == TRIGGER_WITH_NONE

    def test_from_non_built_with_none_values(self):
        assert Trigger.from_non_built(NON_BUILT_TRIGGER_WITH_NONE) == TRIGGER_WITH_NONE

    def test_to_built_with_none_values(self):
        assert TRIGGER_WITH_NONE.to_built() == BUILT_TRIGGER_WITH_NONE

    def test_to_non_built_with_none_values(self):
        assert TRIGGER_WITH_NONE.to_non_built() == NON_BUILT_TRIGGER_WITH_NONE

    def test_from_built_to_built_is_idempotent(self):
        assert Trigger.from_built(BUILT_TRIGGER).to_built() == BUILT_TRIGGER

    def test_from_non_built_to_non_built_is_idempotent(self):
        assert Trigger.from_non_built(NON_BUILT_TRIGGER).to_non_built() == NON_BUILT_TRIGGER

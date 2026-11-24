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

from __future__ import annotations

from typing import cast

import pytest

from mp.core.data_models.common.condition.condition_group import LogicalOperator
from mp.core.data_models.playbooks.trigger.metadata import (
    BuiltTrigger,
    NonBuiltTrigger,
    Trigger,
    TriggerExecutionMode,
    TriggerType,
)

from .constants import (
    BUILT_TRIGGER,
    BUILT_TRIGGER_WITH_NONE,
    NON_BUILT_TRIGGER,
    NON_BUILT_TRIGGER_WITH_NONE,
    TRIGGER,
    TRIGGER_WITH_NONE,
)

FILE_NAME: str = ""


class TestTriggerDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert Trigger.from_built(FILE_NAME, BUILT_TRIGGER) == TRIGGER

    def test_from_non_built_with_valid_data(self) -> None:
        assert Trigger.from_non_built(FILE_NAME, NON_BUILT_TRIGGER) == TRIGGER

    def test_to_built(self) -> None:
        assert TRIGGER.to_built() == BUILT_TRIGGER

    def test_to_non_built(self) -> None:
        assert TRIGGER.to_non_built() == NON_BUILT_TRIGGER

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            Trigger.from_built(FILE_NAME, {})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            Trigger.from_non_built(FILE_NAME, {})

    def test_from_built_with_none_values(self) -> None:
        assert Trigger.from_built(FILE_NAME, BUILT_TRIGGER_WITH_NONE) == TRIGGER_WITH_NONE

    def test_from_non_built_with_none_values(self) -> None:
        assert Trigger.from_non_built(FILE_NAME, NON_BUILT_TRIGGER_WITH_NONE) == TRIGGER_WITH_NONE

    def test_to_built_with_none_values(self) -> None:
        assert TRIGGER_WITH_NONE.to_built() == BUILT_TRIGGER_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert TRIGGER_WITH_NONE.to_non_built() == NON_BUILT_TRIGGER_WITH_NONE

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert Trigger.from_built(FILE_NAME, BUILT_TRIGGER).to_built() == BUILT_TRIGGER

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert Trigger.from_non_built(FILE_NAME, NON_BUILT_TRIGGER).to_non_built() == NON_BUILT_TRIGGER

    def test_case_reaction_trigger_round_trip(self) -> None:
        built_reaction_trigger: BuiltTrigger = {
            "Identifier": "trig-1",
            "IsEnabled": True,
            "DefinitionIdentifier": "case-pb-1",
            "Type": 18,
            "WorkflowName": None,
            "LogicalOperator": 0,
            "Conditions": [
                {
                    "FieldName": "[Case.Priority]",
                    "MatchType": 0,
                    "Value": "High",
                    "CustomOperatorName": None,
                }
            ],
            "Environments": ["Default Environment"],
            "ExecutionMode": 1,
            "ReactionLogicalOperator": 1,
            "ReactionConditions": [
                {
                    "LogicalOperator": 0,
                    "Conditions": [
                        {
                            "FieldName": "from",
                            "MatchType": 10,
                            "Value": "",
                            "CustomOperatorName": None,
                            "Enabled": True,
                        },
                        {
                            "FieldName": "to",
                            "MatchType": 0,
                            "Value": "Critical",
                            "CustomOperatorName": None,
                            "Enabled": True,
                        },
                    ],
                }
            ],
            "MaxReactionDepth": 5,
        }
        trig: Trigger = Trigger.from_built(FILE_NAME, built_reaction_trigger)
        assert trig.type_ == TriggerType.CASE_PRIORITY_CHANGED
        assert trig.execution_mode == TriggerExecutionMode.RESTART
        assert trig.max_reaction_depth == 5
        assert trig.to_built() == built_reaction_trigger

        non_built: NonBuiltTrigger = trig.to_non_built()
        assert non_built["type_"] == "case_priority_changed"
        assert non_built["execution_mode"] == "restart"
        assert non_built["max_reaction_depth"] == 5
        assert Trigger.from_non_built(FILE_NAME, non_built).to_built() == built_reaction_trigger

    @pytest.mark.parametrize(
        ("type_id", "expected_enum"),
        [
            (12, TriggerType.CASE_ASSIGNEE_CHANGED),
            (13, TriggerType.ENTITY_ADDED),
            (14, TriggerType.ALERT_PRIORITY_CHANGED),
            (15, TriggerType.ALERT_CUSTOM_FIELD_CHANGED),
            (16, TriggerType.CASE_CUSTOM_FIELD_CHANGED),
            (17, TriggerType.CASE_STAGE_CHANGED),
            (18, TriggerType.CASE_PRIORITY_CHANGED),
            (19, TriggerType.CASE_TAG_ADDED),
            (20, TriggerType.CASE_COMMENT_ADDED),
        ],
    )
    def test_all_reaction_trigger_types(self, type_id: int, expected_enum: TriggerType) -> None:
        built: BuiltTrigger = {**BUILT_TRIGGER, "Type": type_id}
        trig: Trigger = Trigger.from_built(FILE_NAME, built)
        assert trig.type_ == expected_enum
        assert Trigger.from_non_built(FILE_NAME, trig.to_non_built()).to_built() == built

    def test_reaction_trigger_string_enums_from_built(self) -> None:
        built_str_enums: BuiltTrigger = {
            **BUILT_TRIGGER,
            "ExecutionMode": "RESTART",
            "ReactionLogicalOperator": "OR",
        }
        trig: Trigger = Trigger.from_built(FILE_NAME, built_str_enums)
        assert trig.execution_mode == TriggerExecutionMode.RESTART
        assert trig.reaction_logical_operator == LogicalOperator.OR

        built_unspecified: BuiltTrigger = {
            **BUILT_TRIGGER,
            "ExecutionMode": "WORKFLOW_TRIGGER_EXECUTION_MODE_UNSPECIFIED",
            "ReactionLogicalOperator": "0",
        }
        trig_unspec: Trigger = Trigger.from_built(FILE_NAME, built_unspecified)
        assert trig_unspec.execution_mode == TriggerExecutionMode.UNSPECIFIED
        assert trig_unspec.reaction_logical_operator == LogicalOperator.AND

    def test_reaction_trigger_boolean_enums_raise_value_error(self) -> None:
        with pytest.raises(ValueError, match="Failed to load built"):
            Trigger.from_built(
                FILE_NAME,
                cast("BuiltTrigger", {**BUILT_TRIGGER, "ExecutionMode": True}),
            )
        with pytest.raises(ValueError, match="Failed to load built"):
            Trigger.from_built(
                FILE_NAME,
                cast("BuiltTrigger", {**BUILT_TRIGGER, "ReactionLogicalOperator": False}),
            )

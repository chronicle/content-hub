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

from mp.core.data_models.integrations.action.ai.entity_types import (
    ENTITY_TYPE_TO_DEF_ENTITY_TYPE,
    build_dynamic_entity_prompt_rules,
    get_all_entity_param_examples_string,
)


def test_get_all_entity_param_examples_string() -> None:
    """Test that all entity parameter title examples are generated from ENTITY_TYPE_TO_DEF_ENTITY_TYPE."""
    examples_str = get_all_entity_param_examples_string()
    assert "`User`" in examples_str
    assert "`Address`" in examples_str
    assert "`Host Name`" in examples_str
    assert "`File Hash`" in examples_str
    assert "`Cve`" in examples_str
    assert "`Domain`" in examples_str


def test_build_dynamic_entity_prompt_rules() -> None:
    """Test that prompt rules cover all entity types in ENTITY_TYPE_TO_DEF_ENTITY_TYPE without extraneous words."""
    rules_str = build_dynamic_entity_prompt_rules()
    for field_name, entity_type in ENTITY_TYPE_TO_DEF_ENTITY_TYPE.items():
        param_title = field_name.replace("_", " ").title()
        expected_rule = (
            f"- Parameters representing `{param_title}` -> set `{field_name}: true` "
            f"(maps to `{entity_type.value}`)."
        )
        assert expected_rule in rules_str
    assert "or similar" not in rules_str

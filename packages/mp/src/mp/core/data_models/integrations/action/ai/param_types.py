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

from mp.core.data_models.integrations.action.parameter import ActionParamType

PARAM_TYPE_TO_SYNONYMS: dict[ActionParamType, tuple[str, ...]] = {
    ActionParamType.DDL: (
        "DDL",
        "Dropdown",
        "Drop-down",
        "Drop-down list",
        "Select",
        "Choice",
        "List",
        "Combo Box",
        "Select Box",
        "Picker",
        "Option Menu",
    ),
    ActionParamType.MULTI_CHOICE_PARAMETER: (
        "Multi-Choice",
        "Multi-Select",
        "Multiple Choice",
        "Multi Choice Parameter",
        "Multi Select",
        "Checkbox Group",
        "Tags",
        "Multiple Select",
        "Token Input",
    ),
    ActionParamType.BOOLEAN: (
        "Boolean",
        "Bool",
        "Logical",
        "Flag",
        "Checkbox",
        "Bit",
        "Binary",
        "Toggle",
        "Switch",
        "Yes/No",
        "True/False",
        "On/Off",
    ),
    ActionParamType.STRING: (
        "String",
        "Text",
        "Str",
        "Char",
        "Varchar",
        "Text Field",
        "Plain Text",
    ),
    ActionParamType.INTEGER: (
        "Integer",
        "Int",
        "Number",
        "Numeric",
        "Whole Number",
        "Long",
    ),
    ActionParamType.PASSWORD: (
        "Password",
        "Secret",
        "Sensitive String",
        "Masked",
        "Hidden",
        "Secure String",
        "Credential",
        "Token",
    ),
    ActionParamType.CODE: (
        "Code",
        "Script",
        "Code Block",
        "Snippet",
        "Expression",
        "Query",
        "Raw Code",
        "JSON",
    ),
}


def build_dynamic_param_type_synonym_rules() -> str:
    """Generate bulleted prompt rules for parameter type synonyms.

    Returns:
        str: Bulleted prompt rules for parameter type synonyms.

    """
    rules: list[str] = []
    for param_type, synonyms in PARAM_TYPE_TO_SYNONYMS.items():
        synonyms_str: str = " ≡ ".join(f"`{s}`" for s in synonyms)
        title: str = param_type.name.replace("_", " ")
        rules.append(f"       * {title}: {synonyms_str}")
    return "\n".join(rules)

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
from typing import Any

from pydantic import BaseModel, Field, create_model

from mp.describe.common.metadata import _TYPE_MAPPING, FieldSchemaConfig


def format_display_value(val: object) -> str:
    """Format a value, dictionary, or Pydantic model into a display string for logging.

    Args:
        val: Object or Pydantic model value to format.

    Returns:
        str: Pretty-formatted JSON or string representation.

    """
    if isinstance(val, BaseModel):
        return val.model_dump_json(indent=2)

    if isinstance(val, dict):
        return json.dumps(val, indent=2, default=str)

    return str(val)


def create_dynamic_field_model(
    target_field: str,
    schema_def: FieldSchemaConfig | None = None,
) -> type[BaseModel]:
    """Create a dynamic Pydantic model for a target field fallback.

    Args:
        target_field: The field name to override.
        schema_def: Optional schema configuration details.

    Returns:
        type[BaseModel]: Constructed Pydantic model class.

    """
    model_name: str = (
        schema_def.model_name if schema_def and schema_def.model_name else f"{target_field.title()}Override"
    )
    type_str: str = schema_def.type if schema_def and schema_def.type else "str"
    py_type: Any = _TYPE_MAPPING.get(type_str.lower(), str)
    is_req: bool = schema_def.required if schema_def and schema_def.required is not None else True
    desc: str = schema_def.description if schema_def and schema_def.description else ""

    if is_req:
        field_def = (py_type, Field(..., description=desc))
    else:
        field_def = (py_type | None, Field(default=None, description=desc))

    return create_model(model_name, **{target_field: field_def})  # ty: ignore[no-matching-overload]


def create_nested_schema(model_name: str, schema_dict: dict[str, Any]) -> type[BaseModel]:
    """Recursively create a Pydantic model from a nested dictionary or schema definition.

    Args:
        model_name: Name of the generated model class.
        schema_dict: Dictionary representing field names and types/descriptions/nested dicts.

    Returns:
        type[BaseModel]: Constructed nested Pydantic model class.

    """
    field_definitions: dict[str, Any] = {}

    for key, val in schema_dict.items():
        if isinstance(val, dict):
            nested_model = create_nested_schema(f"{model_name}_{key.title()}", val)
            field_definitions[key] = (nested_model, ...)
        elif isinstance(val, list) and val and isinstance(val[0], dict):
            item_model = create_nested_schema(f"{model_name}_{key.title()}Item", val[0])
            field_definitions[key] = (list[item_model], ...)  # ty: ignore[invalid-type-form]
        elif isinstance(val, type):
            field_definitions[key] = (val, ...)
        elif isinstance(val, str):
            mapped_type = _TYPE_MAPPING.get(val.lower(), str)
            field_definitions[key] = (mapped_type, ...)
        else:
            field_definitions[key] = (type(val) if val is not None else str, ...)

    return create_model(model_name, **field_definitions)


__all__: list[str] = [
    "create_dynamic_field_model",
    "create_nested_schema",
    "format_display_value",
]

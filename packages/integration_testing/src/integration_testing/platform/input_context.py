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

import copy
import json
from typing import TYPE_CHECKING

from TIPCommon.data_models import ScriptContext

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def get_mock_input_context(context: SingleJson | None) -> bytes:
    full_context: ScriptContext = _fill_missing_context(context)
    return json.dumps(full_context.to_json()).encode("utf-8-sig")


def _fill_missing_context(partial_context: SingleJson | None = None) -> ScriptContext:
    default_context: ScriptContext = ScriptContext()

    if partial_context is not None:
        default_context.update(partial_context)

    _set_missing_parameter_values(default_context)

    return default_context


def _set_missing_parameter_values(context: ScriptContext) -> None:
    if context.parameters and not context.connector_context.connector_info.params:
        context.connector_context.connector_info.params = copy.deepcopy(
            context.parameters,
        )

    elif not context.parameters and context.connector_context.connector_info.params:
        context.parameters = copy.deepcopy(
            context.connector_context.connector_info.params,
        )

    context.connector_context.connector_info.params = _restructure_connector_params(
        context.connector_context.connector_info.params,
    )


def _restructure_connector_params(
    connector_params: SingleJson | list[SingleJson],
) -> list[SingleJson]:
    if isinstance(connector_params, dict):
        return [
            {"param_name": name, "param_value": value} for name, value in connector_params.items()
        ]

    if isinstance(connector_params, list):
        return connector_params

    msg: str = f"Wrong type for parameter connector_params: {type(connector_params)}"
    raise TypeError(msg)

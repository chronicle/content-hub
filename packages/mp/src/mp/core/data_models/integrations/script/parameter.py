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

from mp.core.data_models.abc import RepresentableEnum


class ScriptParamType(RepresentableEnum):
    BOOLEAN = 0
    INTEGER = 1
    STRING = 2
    PASSWORD = 3
    IP = 4
    IP_OR_HOST = 5
    URL = 6
    DOMAIN = 7
    EMAIL = 8
    VALUES = 9
    VALUES_AS_SEMICOLON_SEPARATED = 10
    MULTI_VALUE_SELECTION = 11
    SCRIPT = 12
    NUMERICAL_VALUES = 13

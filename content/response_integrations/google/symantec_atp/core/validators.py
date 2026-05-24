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
from .constants import PRIORITIES
from TIPCommon import convert_list_to_comma_string


class SymantecATPValidatorException(Exception):
    pass


class SymantecATPValidator:
    @staticmethod
    def validate_priorities(priorities):
        for priority in priorities:
            if not priority.upper() in PRIORITIES:
                raise SymantecATPValidatorException(
                    f"{priority} not in {convert_list_to_comma_string(PRIORITIES)}"
                )

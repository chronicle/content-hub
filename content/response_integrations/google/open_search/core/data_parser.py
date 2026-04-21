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
from .data_models import DslSearchResult


class OpenSearchParser:
    def build_dsl_result_objects(self, raw_data):
        return [
            self._build_dsl_result_object(dsl_result_dict)
            for dsl_result_dict in raw_data
        ]

    def _build_dsl_result_object(self, dsl_result_dict):
        return DslSearchResult(
            raw_data=dsl_result_dict, alert_id=dsl_result_dict["_id"]
        )

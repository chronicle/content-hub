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
from .datamodels import *


class SymantecEmailSecurityCloudParser:
    def build_ioc_results_list(self, raw_data):
        return [self.build_ioc_result(item) for item in raw_data]

    def build_ioc_result(self, raw_data):
        return IOCResult(
            raw_data=raw_data,
            blacklist_id=raw_data.get("iocBlackListId"),
            ioc_type=raw_data.get("iocType"),
            ioc_value=raw_data.get("iocValue"),
            failure_reason=raw_data.get("failureReason"),
        )

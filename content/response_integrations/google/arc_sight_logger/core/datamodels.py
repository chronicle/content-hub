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
class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class QueryStatus(BaseModel):
    def __init__(self, raw_data, status, result_type, hit, scanned, elapsed, message):
        super(QueryStatus, self).__init__(raw_data)
        self.status = status
        self.result_type = result_type
        self.hit = hit
        self.scanned = scanned
        self.elapsed = elapsed
        self.message = message

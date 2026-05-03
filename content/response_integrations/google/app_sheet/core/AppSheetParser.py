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
from .datamodels import Table, Record

class AppSheetParser:
    def build_search_records_object(self, raw_data):
        return [self.build_search_record_object(item) for item in raw_data]

    def build_search_record_object(self, raw_data):
        return Record(raw_data=raw_data)

    def build_table_list(self, raw_data):
        return [self.build_table_object(item) for item in raw_data]

    def build_table_object(self, raw_data):
        return Table(
            raw_data=raw_data, id=raw_data.get("id"), name=raw_data.get("name")
        )

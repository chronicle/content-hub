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
    """Base model for inheritance"""

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class EndpointResult(BaseModel):
    def __init__(
        self,
        raw_data,
        hostname,
        local_ipv4,
        local_ipv6,
        external_ipv4,
        error,
        tables_data,
        limit,
    ):
        super().__init__(raw_data)
        self.hostname = hostname
        self.local_ipv4 = local_ipv4
        self.local_ipv6 = local_ipv6
        self.external_ipv4 = external_ipv4
        self.error = error
        self.tables_data = tables_data
        self.limit = limit

    def to_json(self):
        if self.limit:
            query_results = self.raw_data.get("osQueryResult", [])

            for query_result in query_results:
                columns_number = len(query_result.get("columns", []))
                query_result["values"] = (
                    query_result.get("values")[: columns_number * self.limit]
                    if query_result.get("values")
                    else []
                )

        return self.raw_data

    def to_tables(self):
        return [self.to_table(table_data) for table_data in self.tables_data]

    def to_table(self, table_data):
        columns_number = len(table_data.columns)
        rows = [
            table_data.values[i * columns_number : (i + 1) * columns_number]
            for i in range(
                (len(table_data.values) + columns_number - 1) // columns_number
            )
        ]

        return [dict(zip(table_data.columns, row, strict=False)) for row in rows[: self.limit]]


class TableData:
    def __init__(self, columns, values):
        self.columns = columns
        self.values = values

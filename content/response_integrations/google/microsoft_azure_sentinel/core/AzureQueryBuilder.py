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
from enum import Enum
from datetime import datetime, timedelta


class QueryOperatorEnum(Enum):
    AND = "and"
    OR = "or"


class OperatorEnum(Enum):
    EQ = "eq"
    GE = "ge"


class Condition:
    def __init__(
        self,
        *,
        field,
        operator,
        value,
        join_values_with=None,
        value_with_quotes=False,
        value_formatter=None,
    ):
        self.is_valid_condition = bool(value)
        self.field = field
        self.operator = operator
        self.value = value
        self.value_with_quotes = value_with_quotes
        self.join_values_with = f" {join_values_with or QueryOperatorEnum.OR.value} "

        if value_formatter:
            method, *args = value_formatter
            getattr(self, method)(*args)

    def __str__(self):
        conditions = self.to_query()
        query = self.join_values_with.join(conditions)
        return f"({query})"
        # return f'({query})' if len(conditions) > 1 else query

    def to_query(self):
        field = "'{}'" if self.value_with_quotes else "{}"
        values = self.value if isinstance(self.value, list) else [self.value]
        return [
            f"{self.field} {self.operator} {field.format(value)}" for value in values
        ]

    def format_time(self, formatter):
        if self.is_valid_condition:
            self.value = self.value.strftime(formatter)

    def set_hours_back(self, formatter):
        if self.is_valid_condition:
            self.value = (
                datetime.utcnow() - timedelta(hours=int(self.value))
            ).strftime(formatter)


class QueryBuilder:
    def __init__(self, conditions, join_with=None):
        self.conditions = conditions
        self.join_with = (
            join_with or f" {QueryOperatorEnum.AND.value} "
            if len(conditions) > 1
            else ""
        )

    def __str__(self):
        return self.join_with.join(self.build_query())

    def build_query(self):
        return [
            str(condition)
            for condition in self.conditions
            if condition.is_valid_condition
        ]

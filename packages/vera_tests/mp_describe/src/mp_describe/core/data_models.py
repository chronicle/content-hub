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

from typing import Annotated, Self, override

from pydantic import Field
from vera import CsvColumn, CsvRow, ScoreRange, TestCase, TestCaseInput, TestCaseOutput


class MyPluginInput(TestCaseInput):
    user_query: str

    @override
    def to_description_prompt(self) -> str:
        return f"User Input: {self.user_query}"


class MyPluginOutput(TestCaseOutput):
    response: str

    @override
    def to_output_description_prompt(self) -> str:
        return f"Model Response: {self.response}"


class MyPluginTestCase(TestCase):
    input: MyPluginInput


class LlmColumns(CsvColumn):
    llm_field_score_1: int
    llm_field_score_reason_1: str


class StaticCheckColumns(CsvColumn):
    static_field_score_1: int
    static_field_score_reason_1: str


class MyPluginRow(CsvRow[MyPluginInput, MyPluginOutput, LlmColumns, StaticCheckColumns]):
    name: Annotated[str, Field(alias="Test Case Name")]
    llm_field_score_1: int
    llm_field_score_reason_1: str
    static_field_score_1: int
    static_field_score_reason_1: str

    @override
    def calculate_final_score(self) -> float:
        return sum([self.llm_field_score_1, self.static_field_score_1]) / 2

    @property
    @override
    def score_range(self) -> ScoreRange:
        return ScoreRange(min=1, max=5)

    @classmethod
    @override
    def from_columns(
        cls,
        test_case: TestCase[MyPluginInput],
        test_output: MyPluginOutput,
        llm_checks_columns: CsvColumn,
        static_checks_columns: CsvColumn,
    ) -> Self:
        row = cls.model_validate(
            {
                "identifier": test_case.id,
                "name": test_case.name,
                "final_score": 5.0,  # Placeholder
            },
            by_name=True,
        )
        row.final_score = row.calculate_final_score()
        return row

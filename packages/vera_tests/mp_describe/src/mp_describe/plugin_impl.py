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

import pathlib
from collections.abc import Iterable
from typing import Any

import anyio
import yaml

import vera
from vera import CsvColumn, TestCase
from .core.data_models import MyPluginInput, MyPluginOutput, MyPluginRow, MyPluginTestCase
from .core.mp_describe import run_my_feature
from .core.static_tests import StaticTester

FEATURE_TESTS_DIR: pathlib.Path = pathlib.Path(__file__).parent / "feature_tests"
ASYNC_FEATURE_TESTS_DIR: anyio.Path = anyio.Path(__file__).parent / "feature_tests"


@vera.hook_impl
def get_test_cases() -> Iterable[TestCase[MyPluginInput]]:
    """Hook to load test cases. By default, it looks for feature_testing/test_cases.yaml."""
    # Example implementation:
    # import pathlib
    # test_cases_file = pathlib.Path(__file__).parent / "feature_testing" / "test_cases.yaml"
    # with open(test_cases_file, "r") as f:
    #     data = yaml.safe_load(f)
    #     return [TestCase(input=MyPluginInput(**d["input"]), **d) for d in data]
    test_cases_file: pathlib.Path = FEATURE_TESTS_DIR / "test_cases.yaml"
    file_content: str = test_cases_file.read_text(encoding="utf-8")
    test_cases: list[dict[str, Any]] = yaml.safe_load(file_content)
    return [MyPluginTestCase(**tc) for tc in test_cases]


@vera.hook_impl
async def run_feature(
    test_case: TestCase[MyPluginInput],
    resources_dir: anyio.Path,
) -> MyPluginOutput:
    """
    Execute the feature being tested. This is where you call your LLM or API.
    """
    # result = await your_ai_logic(test_case.input.user_query)
    # return MyPluginOutput(response=result)
    return run_my_feature(test_case, resources_dir)


@vera.hook_impl
def run_static_tests(
    test_case: TestCase[MyPluginInput],
    test_output: MyPluginOutput,
) -> CsvColumn:
    """Perform programmatic checks on the output (e.g., JSON validation, keyword checks)."""
    return StaticTester(test_case, test_output).run_static_tests()


@vera.hook_impl
def get_csv_row_class() -> type[MyPluginRow]:
    """Return the Pydantic class used for a single row in the final CSV report."""
    return MyPluginRow


@vera.hook_impl
def get_llm_csv_columns_class() -> type[CsvColumn]:
    """Return the Pydantic class used for the LLM Judge's evaluation columns."""
    return CsvColumn


@vera.hook_impl
def get_llm_specs_dir() -> anyio.Path:
    """Return the path to the directory containing Markdown evaluation specs."""
    return ASYNC_FEATURE_TESTS_DIR / "specs"

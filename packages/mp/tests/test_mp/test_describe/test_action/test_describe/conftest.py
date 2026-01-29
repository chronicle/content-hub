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

from typing import Any

import anyio
import pytest
import yaml


@pytest.fixture
def expected_results_file() -> anyio.Path:
    return anyio.Path(__file__).parent / "expected_results.yaml"


@pytest.fixture
async def expected_results(expected_results_file: anyio.Path) -> dict[str, dict[str, Any]]:
    content: str = await expected_results_file.read_text(encoding="utf-8")
    return yaml.safe_load(content)


@pytest.fixture
def ping_expected_results(
    expected_results: dict[str, dict[str, Any]],
    ping_action: anyio.Path,
) -> dict[str, Any]:
    return expected_results[ping_action.name]

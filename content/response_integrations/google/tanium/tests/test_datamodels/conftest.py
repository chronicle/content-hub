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

import json
from typing import Any

import pytest

from tanium.tests.common import TEST_INTEGRATION_PATH

from tanium.core.datamodels import QuestionResultFullData


QUESTION_RESULT_FIXTURE_PATH = (
    TEST_INTEGRATION_PATH / "data" / "question_result_raw_data.json"
)

# pylint: disable=redefined-outer-name


@pytest.fixture(scope="module")
def question_result_raw_data() -> dict | list[dict[str, Any]]:
    """Provides the raw API response fixture."""
    return json.loads(QUESTION_RESULT_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def question_result(
    question_result_raw_data: dict[str, Any],  # pylint: disable=redefined-outer-name
) -> QuestionResultFullData:
    """Provides an initialized QuestionResultFullData instance."""
    return QuestionResultFullData.from_raw_response(raw_data=question_result_raw_data)

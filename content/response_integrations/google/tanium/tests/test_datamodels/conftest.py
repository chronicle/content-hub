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

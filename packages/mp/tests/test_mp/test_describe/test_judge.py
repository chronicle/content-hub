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

"""Unit tests for LLM Judge evaluator in regression testing."""

from __future__ import annotations

from unittest import mock

import pytest

from mp.describe.regression_test.judge import (
    JudgeEvaluationResult,
    JudgeVerdict,
    TextCandidate,
    create_judge_prompt,
    evaluate_text_equivalence_batch,
    run_judge_evaluation_sync,
)


def test_create_judge_prompt() -> None:
    candidate = TextCandidate(
        entry_path="ai_description",
        baseline_text="Old description",
        test_text="New description",
    )
    prompt = create_judge_prompt(candidate)
    assert "Old description" in prompt
    assert "New description" in prompt
    assert "Evaluate whether these two text fields are semantically equivalent" in prompt


@pytest.mark.anyio
async def test_evaluate_text_equivalence_batch_empty() -> None:
    results = await evaluate_text_equivalence_batch([])
    assert results == []


@pytest.mark.anyio
async def test_evaluate_text_equivalence_batch_success() -> None:
    candidate = TextCandidate(
        entry_path="ai_description",
        baseline_text="Text 1",
        test_text="Text 2",
    )
    verdict = JudgeVerdict(
        prompt_intent_analysis="Intent",
        field_1_core_claims=["Claim 1"],
        field_2_core_claims=["Claim 2"],
        comparison_reasoning="Same meaning",
        verdict="EQUIVALENT",
    )

    mock_llm = mock.AsyncMock()
    mock_llm.send_bulk_messages.return_value = [verdict]

    results: list[JudgeEvaluationResult] = await evaluate_text_equivalence_batch(
        [candidate],
        llm=mock_llm,
    )
    assert len(results) == 1
    assert results[0].entry_path == "ai_description"
    assert results[0].verdict.verdict == "EQUIVALENT"
    mock_llm.send_bulk_messages.assert_called_once()


def test_run_judge_evaluation_sync() -> None:
    candidate = TextCandidate(
        entry_path="ai_description",
        baseline_text="Text 1",
        test_text="Text 2",
    )
    with mock.patch(
        "mp.describe.regression_test.judge.evaluate_text_equivalence_batch",
        return_value=[
            JudgeEvaluationResult(
                entry_path="ai_description",
                baseline_text="Text 1",
                test_text="Text 2",
                verdict=JudgeVerdict(
                    prompt_intent_analysis="Intent",
                    field_1_core_claims=["C1"],
                    field_2_core_claims=["C2"],
                    comparison_reasoning="Reasoning",
                    verdict="EQUIVALENT",
                ),
            )
        ],
    ) as mock_batch:
        results = run_judge_evaluation_sync([candidate])

    assert len(results) == 1
    assert results[0].verdict.verdict == "EQUIVALENT"
    mock_batch.assert_called_once_with([candidate], use_batch=False)


def test_judge_verdict_resilience() -> None:
    # 1. Lowercase 'not_equivalent' with alias 'reasoning'
    v1 = JudgeVerdict.model_validate({"verdict": "not_equivalent", "reasoning": "diff"})
    assert v1.verdict == "NOT_EQUIVALENT"
    assert v1.comparison_reasoning == "diff"

    # 2. Missing verdict key defaults to EQUIVALENT
    v2 = JudgeVerdict.model_validate({"explanation": "The texts are EQUIVALENT in meaning."})
    assert v2.verdict == "EQUIVALENT"

    # 3. Completely empty dict defaults to EQUIVALENT
    v3 = JudgeVerdict.model_validate({})
    assert v3.verdict == "EQUIVALENT"
    assert v3.change_type == "EQUIVALENT"


def test_judge_verdict_operational_materiality_fields() -> None:
    # 1. NOT_EQUIVALENT with change_type conflict and missing facts
    v1 = JudgeVerdict.model_validate(
        {
            "verdict": "NOT_EQUIVALENT",
            "change_type": "GENERATION_CONFLICT",
            "missing_operational_facts": ["Rate limit 100 req/min missing"],
        }
    )
    assert v1.verdict == "NOT_EQUIVALENT"
    assert v1.change_type == "GENERATION_CONFLICT"
    assert v1.missing_operational_facts == ["Rate limit 100 req/min missing"]

    # 2. EQUIVALENT forces change_type to EQUIVALENT
    v2 = JudgeVerdict.model_validate(
        {
            "verdict": "EQUIVALENT",
            "change_type": "GENERATOR_REGRESSION",
        }
    )
    assert v2.verdict == "EQUIVALENT"
    assert v2.change_type == "EQUIVALENT"

    # 3. NOT_EQUIVALENT with missing change_type defaults to GENERATOR_REGRESSION
    v3 = JudgeVerdict.model_validate({"verdict": "NOT_EQUIVALENT"})
    assert v3.verdict == "NOT_EQUIVALENT"
    assert v3.change_type == "GENERATOR_REGRESSION"
    assert v3.missing_operational_facts == []

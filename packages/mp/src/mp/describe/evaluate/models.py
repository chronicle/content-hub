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

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class VerdictEnum(StrEnum):
    """Evaluation verdict outcome."""

    PASS = "PASS"  # ruff: ignore[hardcoded-password-string]
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


class RuleVerdict(BaseModel):
    """Schema for individual rule evaluation verdict returned by LLM."""

    rule_evaluated: str = Field(description="Name/Title of the rule evaluated")
    verdict: VerdictEnum = Field(description="Verdict: PASS, FAIL, or PARTIAL")
    reasoning: str = Field(description="Step-by-step logical justification with code evidence")
    suggested_fix: str | None = Field(default=None, description="Suggested fix if FAIL or PARTIAL, else null")


class RuleEvaluationResult(BaseModel):
    """Record schema for a single persisted rule evaluation in database."""

    evaluation_id: str
    integration_id: str
    action_id: str
    run_id: str
    evaluated_at: str
    rule_title: str
    actual_value: str = ""
    verdict: VerdictEnum
    reasoning: str
    suggested_fix: str | None = None
    prompt: str | None = None


class EvaluationReport(BaseModel):
    """Aggregated evaluation report for an integration run."""

    integration_id: str
    run_id: str
    evaluated_at: str
    total_evaluations: int
    pass_count: int
    fail_count: int
    partial_count: int
    score_percentage: float
    results: list[RuleEvaluationResult]
    analyzed_files: list[str] = Field(
        default_factory=list, description="List of input file paths analyzed during evaluation"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert evaluation report to dictionary representation.

        Returns:
            Dictionary containing model fields.

        """
        return self.model_dump()

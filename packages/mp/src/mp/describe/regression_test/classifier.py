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

"""Deterministic provenance-aware classification of semantic verdicts for mp describe-regression-test."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from mp.describe.regression_test.judge import JudgeVerdict, SemanticAssessment, TextCandidate

logger = logging.getLogger(__name__)

ChangeType = Literal["EQUIVALENT", "GENERATOR_REGRESSION", "GENERATION_CONFLICT", "AMBIGUOUS_CHANGE"]
GateDecision = Literal["PASS", "BLOCK", "REVIEW"]


class ChangeClassifier:
    """Classify the origin of a text change deterministically without asking the LLM to guess."""

    @staticmethod
    def classify(
        assessment: SemanticAssessment,
        _candidate: TextCandidate | None = None,
    ) -> tuple[ChangeType, GateDecision, str]:
        """Classify a semantic assessment into a change type, CI gate decision, and audit reasoning.

        Args:
            assessment: Semantic assessment returned by Gemini Judge.
            _candidate: Optional TextCandidate containing file and path metadata.

        Returns:
            tuple[ChangeType, GateDecision, str]: The change type, gate decision, and reasoning.

        """
        if assessment.verdict == "EQUIVALENT":
            return (
                "EQUIVALENT",
                "PASS",
                "The texts are operationally equivalent; no text-contract failure.",
            )

        # For automated regression testing against baseline repository metadata,
        # a non-equivalent semantic mismatch is classified as a GENERATOR_REGRESSION
        # that blocks unattended CI.
        return (
            "GENERATOR_REGRESSION",
            "BLOCK",
            "Action code and schema unchanged; non-equivalent text attributed to generator regression.",
        )

    def build_verdict(
        self,
        assessment: SemanticAssessment,
        candidate: TextCandidate | None = None,
    ) -> JudgeVerdict:
        """Build a complete JudgeVerdict from a SemanticAssessment and candidate provenance.

        Args:
            assessment: Semantic assessment from Gemini Judge.
            candidate: Optional TextCandidate being evaluated.

        Returns:
            JudgeVerdict: Full verdict including deterministic classification.

        """
        from mp.describe.regression_test.judge import JudgeVerdict  # ruff:ignore[import-outside-top-level]

        change_type, gate_decision, reason = self.classify(assessment, candidate)

        data = assessment.model_dump()
        data["change_type"] = change_type
        data["gate_decision"] = gate_decision
        if not data.get("comparison_reasoning"):
            data["comparison_reasoning"] = reason

        return JudgeVerdict.model_validate(data)

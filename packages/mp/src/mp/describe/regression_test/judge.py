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

"""Module implementing an LLM-as-a-Judge semantic evaluator for text regression testing."""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import time
from typing import Literal, cast

from pydantic import BaseModel, Field, model_validator

from mp.core.llm.gemini import Gemini, GeminiConfig

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT: str = """You are an expert AI evaluator acting as an automated gatekeeper for the **Google Chronicle SOAR** (Security Orchestration, Automation, and Response) platform.

Your task is to compare two text fields: Field 1 (Baseline) and Field 2 (Candidate). These texts are not generic paragraphs; they are strict technical descriptions and execution constraints for over **300+ integrations** within the Chronicle ecosystem. You must determine if they are **semantically and operationally equivalent** from the perspective of an autonomous AI Agent executing code based on this data.

### Core Principle: Decision-Critical Information vs. Cosmetic/Backend Noise
You must ruthlessly protect operational constraints while completely forgiving structural and formatting changes.

### Rules for Evaluation:
1. **Parameter & Constraint Integrity (CRITICAL):**
   - IF the Candidate drops a parameter, alters a data type, or shifts applicability requirements (e.g., Mandatory to Optional) -> **NOT_EQUIVALENT**.
   - IF the Candidate introduces operational limits, conditions, or validation constraints not explicitly stated in the Baseline -> **NOT_EQUIVALENT**.
   - IF the Candidate reverses or negates the logical intent of an action -> **NOT_EQUIVALENT**.

2. **Flow & Core Intent Descriptions:**
   - IF logical workflow steps or sequential actions are omitted -> **NOT_EQUIVALENT**.
   - IF the Candidate drops the core declarative action entirely, leaving only secondary notes or parameters -> **NOT_EQUIVALENT**.
   - Exception: Omitting purely decorative headers or redundant introductory clauses is EQUIVALENT, provided the underlying facts remain intact.

3. **Zero Tolerance for Semantic Typos & Broken Grammar:**
   - IF the Candidate introduces typographical errors that result in valid but contextually incorrect English words (semantic drift), or severely misspells technical identifiers -> **NOT_EQUIVALENT**. The Agent must not be forced to guess the intent.
   - IF the Candidate's syntax is so severely degraded, disjointed, or choppy that it loses professional readability and syntactic structure (e.g., stripping structural words to form 'caveman' sentences like 'Severity threshold DDL no define') -> **NOT_EQUIVALENT**.
   - Exception: Minor omissions of articles or auxiliary words that do not disrupt the natural reading flow -> **EQUIVALENT**.

4. **Format & Markdown Agnosticism (FORGIVE):**
   - IF the Candidate cleanly flattens tables, removes styling tags, or alters delimiters while preserving the distinct boundaries between parameters -> **EQUIVALENT**.
   - Deep synonyms for data structures are **EQUIVALENT** as long as the structural mapping is logically sound.
   - EXTREME FLATTENING EXCEPTION: IF formatting removal results in a grammarless contiguous sequence of tokens where the mapping between a parameter's name, its data type, and its required status is destroyed or relies on pure guesswork without delimiters or natural language (e.g., 'Username string yes' instead of 'Username (String, Required)' or 'Username is a required string') -> **NOT_EQUIVALENT**.

5. **Backend Protocol Noise vs. Infrastructure (CRITICAL DISTINCTION):**
   - Exposing or adding generic network, transport, or standard authentication protocols -> **EQUIVALENT**.
   - Hallucinating specific unmentioned infrastructure, architectural components, or proprietary databases -> **NOT_EQUIVALENT**.

### Output Schema Instructions:
You must output a strict JSON object based on the schema. Follow this logic:
- `prompt_intent_analysis`: Briefly state what the text is describing.
- `field_1_core_claims` & `field_2_core_claims`: Extract facts, keeping parameter-to-type mappings intact.
- `missing_operational_facts`: CRITICAL: List BOTH any facts from Field 1 missing in Field 2, AND any illegal constraints/infrastructure hallucinated in Field 2.
- `comparison_reasoning`: Explain the difference step-by-step using the 'Rules for Evaluation' above.
- `verdict`: Categorical determination strictly based on operational materiality.
"""


class JudgeVerdict(BaseModel):
    """Structured Pydantic schema for the LLM Judge verdict."""

    prompt_intent_analysis: str = Field(
        default="", description="Briefly state what the original prompt is asking for."
    )
    field_1_core_claims: list[str] = Field(
        default_factory=list, description="List of core claims/facts extracted from Field 1."
    )
    field_2_core_claims: list[str] = Field(
        default_factory=list, description="List of core claims/facts extracted from Field 2."
    )
    missing_operational_facts: list[str] = Field(
        default_factory=list,
        description="List of critical operational facts or constraints present in baseline but lost in test.",
    )
    comparison_reasoning: str = Field(
        default="",
        description="A step-by-step logical comparison explaining why the core meanings are identical or different.",
    )
    verdict: Literal["EQUIVALENT", "NOT_EQUIVALENT"] = Field(
        default="EQUIVALENT",
        description="Categorical determination: EQUIVALENT or NOT_EQUIVALENT.",
    )
    change_type: Literal[
        "EQUIVALENT", "GENERATOR_REGRESSION", "GENERATION_CONFLICT", "AMBIGUOUS_CHANGE"
    ] = Field(
        default="EQUIVALENT",
        description=(
            "Classification of the change: EQUIVALENT, GENERATOR_REGRESSION (critical operational fact lost), "
            "GENERATION_CONFLICT (generated text contradicts deterministic schema), or AMBIGUOUS_CHANGE."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_verdict(cls, values: dict[str, object] | object) -> dict[str, object] | object:
        if not isinstance(values, dict):
            return values
        val_dict = cast("dict[str, object]", values)

        if not val_dict.get("comparison_reasoning") and val_dict.get("reasoning"):
            val_dict["comparison_reasoning"] = str(val_dict["reasoning"])

        verdict = str(val_dict.get("verdict", "EQUIVALENT")).strip().upper()
        val_dict["verdict"] = "NOT_EQUIVALENT" if "NOT_EQUIVALENT" in verdict else "EQUIVALENT"

        if val_dict["verdict"] == "EQUIVALENT":
            val_dict["change_type"] = "EQUIVALENT"
        elif val_dict.get("change_type") not in {
            "GENERATOR_REGRESSION",
            "GENERATION_CONFLICT",
            "AMBIGUOUS_CHANGE",
        }:
            val_dict["change_type"] = "GENERATOR_REGRESSION"

        return values


@dataclasses.dataclass
class TextCandidate:
    """Dataclass representing a candidate pair of mismatched text fields to be evaluated."""

    entry_path: str
    baseline_text: str
    test_text: str
    path_of_files: str | None = None
    baseline_file: str | None = None
    test_file: str | None = None


@dataclasses.dataclass
class JudgeEvaluationResult:
    """Dataclass holding the evaluated verdict for a text candidate."""

    entry_path: str
    baseline_text: str
    test_text: str
    verdict: JudgeVerdict
    candidate: TextCandidate | None = None


def create_judge_prompt(candidate: TextCandidate) -> str:
    """Construct prompt for semantic evaluation of two text fields.

    Args:
        candidate: TextCandidate containing baseline and test string.

    Returns:
        str: Formatted evaluation prompt for Gemini Judge.

    """
    return f"""Evaluate whether these two text fields for `{candidate.entry_path}` are semantically equivalent:

1. Text Field 1 (Baseline):
\"\"\"
{candidate.baseline_text}
\"\"\"

2. Text Field 2 (Test/Generated):
\"\"\"
{candidate.test_text}
\"\"\"
"""


async def evaluate_text_equivalence_batch(
    candidates: list[TextCandidate],
    *,
    llm: Gemini | None = None,
    use_batch: bool = False,
) -> list[JudgeEvaluationResult]:
    """Asynchronously evaluate a batch of text candidates for semantic equivalence using Gemini LLM Judge.

    Args:
        candidates: List of candidate text pairs to evaluate.
        llm: Optional pre-configured Gemini SDK instance.
        use_batch: Whether to use Google GenAI Batch API instead of concurrent interactive requests.

    Returns:
        list[JudgeEvaluationResult]: List of evaluated verdicts.

    """
    if not candidates:
        return []

    start_time: float = time.perf_counter()
    prompts: list[str] = [create_judge_prompt(candidate) for candidate in candidates]

    close_after: bool = False
    if llm is None:
        config = GeminiConfig()
        config.use_thinking = True
        config.temperature = 0.0
        llm = Gemini(config)
        close_after = True
    else:
        llm.config.use_thinking = True
        llm.config.temperature = 0.0

    try:
        # Override system prompt with our specialized Judge prompt protocol
        llm.system_prompt = JUDGE_SYSTEM_PROMPT
        responses = await llm.send_bulk_messages(
            prompts, response_json_schema=JudgeVerdict, use_batch=use_batch
        )
    except Exception:
        logger.exception("LLM Judge bulk evaluation failed")
        return []
    finally:
        if close_after:
            await llm.close()

    results: list[JudgeEvaluationResult] = []
    for candidate, response in zip(candidates, responses, strict=False):
        if isinstance(response, JudgeVerdict):
            results.append(
                JudgeEvaluationResult(
                    entry_path=candidate.entry_path,
                    baseline_text=candidate.baseline_text,
                    test_text=candidate.test_text,
                    verdict=response,
                    candidate=candidate,
                )
            )
        else:
            logger.warning(
                "Could not parse JudgeVerdict for %s (got %s)",
                candidate.entry_path,
                type(response),
            )

    elapsed_seconds: float = time.perf_counter() - start_time
    logger.info("LLM Judge evaluated %d candidate(s) in %.1fs", len(candidates), elapsed_seconds)
    return results


def run_judge_evaluation_sync(
    candidates: list[TextCandidate],
    *,
    use_batch: bool = False,
) -> list[JudgeEvaluationResult]:
    """Execute asynchronous bulk evaluation of text candidates synchronously.

    Args:
        candidates: List of TextCandidate items.
        use_batch: Whether to use Google GenAI Batch API.

    Returns:
        list[JudgeEvaluationResult]: Results from the LLM Judge.

    """
    if not candidates:
        return []
    try:
        return asyncio.run(evaluate_text_equivalence_batch(candidates, use_batch=use_batch))
    except RuntimeError:
        # Handle cases where an event loop is already running
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            evaluate_text_equivalence_batch(candidates, use_batch=use_batch)
        )

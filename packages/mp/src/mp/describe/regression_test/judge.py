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

JUDGE_SYSTEM_PROMPT: str = (
    "You are an expert quality assurance evaluator and semantic judge for Google SecOps SOAR integrations. Your task "
    "is to determine if two user-facing action descriptions are semantically equivalent with respect to "
    "**Action Operational Behavior (Operational Materiality)**.\n\n"
    "### Core Principle: Decision-Critical Information vs. Backend Noise\n\n"
    "You must evaluate whether Text Field 1 (Baseline) and Text Field 2 (Test/Candidate) provide an AI Agent "
    "with an equivalent understanding of the action's purpose, applicability, prerequisites, parameters, "
    "and behavior.\n\n"
    "- **EQUIVALENT**: The phrasing or structure may differ, but an AI Agent using either version will:\n"
    "  1. Choose the same action;\n"
    "  2. Apply it under the exact same applicability conditions and entity prerequisites;\n"
    "  3. Populate parameters identically;\n"
    "  4. Expect the same execution scope, security boundaries, and side effects;\n"
    "  5. Expect the same result.\n"
    "- *Ignore Cosmetic & Verbosity Differences*: Grammatical structure, Markdown formatting (e.g., bullet points "
    "vs. paragraphs), tone, and verbosity MUST be ignored.\n"
    "- *Ignore Synonymous UI Data Types*: In parameter tables, differences in naming synonymous UI data types "
    "(e.g., DDL vs. Dropdown, Boolean vs. Bool) MUST be evaluated as EQUIVALENT.\n"
    "- **Strict Data Type & Constraint Enforcements**: You MUST mark NOT_EQUIVALENT if the change alters structural "
    "UI data types (e.g., changing a dropdown list `DDL` to a free-text `String`), changes `Mandatory`/Optional "
    "flags.\n\n"
    "- **NOT_EQUIVALENT**: The candidate description omits or distorts decision-critical information capable of "
    "changing an AI Agent's execution behavior, including:\n"
    "  1. Any logical workflow sequences, flow descriptions, or steps explicitly provided in the baseline (if it was included in the AI description, it MUST be treated as important context);\n"
    "  1a. When to choose or NOT choose the action (e.g., entity prerequisites, required identifier formats, "
    "applicability);\n"
    "  2. What parameter values to pass or which parameters are mandatory;\n"
    "  3. What execution scope, target environment, or side effects to expect;\n"
    "  4. What critical operational boundaries (security constraints, rate limits, retries, timeouts) to observe.\n\n"
    "### Intra-Field Information Relocation Rule\n\n"
    "1. **Intra-Field Relocation**: Relocating information *within logical sections of the same description* "
    "(e.g., moving a note from 'General Description' to 'Additional Notes' within `ai_description`) "
    "is **EQUIVALENT**.\n"
    "2. **Strict Contract Boundary**: Cross-field relocation between incompatible contracts (e.g., moving workflow "
    "logic from `ai_description` into parameter tables in `parameters_description`) is **NOT_EQUIVALENT**.\n"
    "3. **Zero Tolerance for Typos**: Any introduction of spelling errors, typographical mistakes, or strangely corrupted words in the Candidate that are absent in the Baseline makes it strictly **NOT_EQUIVALENT**.\n\n"
    "### Step-by-Step Evaluation Protocol\n\n"
    "1. **Analyze Decision-Critical Intent**: Identify the core applicability conditions, entity prerequisites, "
    "parameters, and operational boundaries expected by an AI Agent.\n"
    "2. **Deconstruct Baseline & Candidate**: Extract essential operational claims and constraints.\n"
    "3. **Map & Compare**: Identify any decision-critical operational facts present in Baseline but lost in Candidate "
    "(`missing_operational_facts`).\n"
    "4. **Classify Change Type**: If NOT_EQUIVALENT, determine if it is `GENERATOR_REGRESSION` (critical fact lost) "
    "or `GENERATION_CONFLICT` (generated text contradicts deterministic parameter schema).\n"
    "5. **Formulate Verdict**: Make your final categorical determination strictly on operational materiality.\n"
)


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

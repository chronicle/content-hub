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
    "### Evaluation Criteria\n\n"
    "You must evaluate whether Text Field 1 (Baseline) and Text Field 2 (Test/Candidate) are **semantically equal** "
    "in how they describe and guide action execution.\n\n"
    "- **EQUIVALENT**: Both descriptions guide action execution identically (specifying the same "
    "action selection conditions, supplying identical parameters, expecting the same execution scope, "
    "and adhering to the same rate limits or security constraints).\n"
    "- *Ignore Cosmetic & Verbosity Differences*: Minor grammatical differences, syntax, Markdown formatting (e.g., "
    "bullet points vs. paragraphs), tone, and verbosity must be ignored. If the operational meaning is preserved, "
    "they are EQUIVALENT.\n"
    "- *Ignore Internal Backend Data Sorting & Heuristics*: Differences in secondary phrasing or omission of internal "
    "backend data sorting or fallback heuristics (such as 'uses newest threat if no active threats found') must be "
    "evaluated as EQUIVALENT.\n"
    "- **NOT_EQUIVALENT**: The candidate description conveys different facts, contradictory conclusions, or omits "
    "a critical operational mechanism present in the baseline (such as retries, rate limits, timeouts, or required "
    "authentication keys). For parameter tables (`parameters_description`), any change or mismatch in parameter "
    "names, data types (e.g., DDL vs String, Boolean vs String), or mandatory flags MUST be evaluated as "
    "NOT_EQUIVALENT.\n\n"
    "### Rules for Borderline Cases & Supplementary Notes\n\n"
    "1. **Supplementary Notes / Additional Phrasing**: Differences in phrasing of supplementary notes are NOT "
    "regressions. Do NOT mark NOT_EQUIVALENT unless there is a genuine factual contradiction or an omission of a "
    "critical operational mechanism (such as retries, rate limits, or required authentication keys).\n"
    "2. **Tie-Breaker Rule**: When two descriptions agree on the primary purpose, API endpoints, and general flow, "
    "but differ only in supplementary fluff or secondary notes (e.g., internal data sorting or fallback heuristics), "
    "you MUST default to **EQUIVALENT**.\n\n"
    "### Intra-Field Information Relocation Rule\n\n"
    "1. **Intra-Field Relocation**: Information relocation *within logical sections of the same "
    "user-facing description*\n"
    "(e.g., moving an informational note from 'General Description' to 'Additional Notes' or 'Flow Description'\n"
    "within `ai_description`) is **EQUIVALENT**.\n"
    "2. **Strict Contract Boundary**: Never allow cross-field relocation between incompatible contracts (e.g., moving "
    "core operational workflow logic from `ai_description` into parameter tables in `parameters_description`).\n\n"
    "### Step-by-Step Evaluation Protocol\n\n"
    "1. **Analyze Operational Intent**: Identify the core operational facts, API endpoints, parameters, and "
    "constraints\n"
    "expected by a SOAR AI agent.\n"
    "2. **Deconstruct Baseline (Field 1)**: Extract essential operational claims and constraints.\n"
    "3. **Deconstruct Candidate (Field 2)**: Extract essential operational claims and constraints.\n"
    "4. **Map & Compare**: Identify any critical operational facts present in Baseline but missing in Candidate "
    "(`missing_operational_facts`).\n"
    "5. **Classify Change Type**: If NOT_EQUIVALENT, determine if it is `GENERATOR_REGRESSION` (critical fact lost "
    "in description) or `GENERATION_CONFLICT` (generated text contradicts deterministic parameter schema).\n"
    "6. **Formulate Verdict**: Make your final categorical determination based strictly on operational materiality.\n"
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
    def _map_aliases_and_defaults(  # ruff:ignore[complex-structure,too-many-branches,too-many-statements]
        cls, values: dict[str, object] | object
    ) -> dict[str, object] | object:
        if isinstance(values, dict):
            val_dict = cast("dict[str, object]", values)
            # 1. Map reasoning alias
            if not val_dict.get("comparison_reasoning") and val_dict.get("reasoning"):
                val_dict["comparison_reasoning"] = str(val_dict["reasoning"])

            # 2. Map verdict aliases from Flash models
            verdict_val = val_dict.get("verdict")
            if verdict_val is None:
                for alias in (
                    "result",
                    "decision",
                    "status",
                    "equivalence",
                    "evaluation",
                    "judgment",
                    "answer",
                    "outcome",
                    "category",
                    "is_equivalent",
                ):
                    if alias in val_dict and val_dict[alias] is not None:
                        verdict_val = val_dict[alias]
                        break

            # 3. If still None, inspect string values in dict for EQUIVALENT / NOT_EQUIVALENT
            if verdict_val is None:
                for v in val_dict.values():
                    if isinstance(v, str):
                        v_up = v.upper()
                        if "NOT_EQUIVALENT" in v_up or "NOT EQUIVALENT" in v_up:
                            verdict_val = "NOT_EQUIVALENT"
                            break
                        if "EQUIVALENT" in v_up:
                            verdict_val = "EQUIVALENT"
                            break

            # 4. Normalize verdict value to exact Literal
            if verdict_val is not None:
                v_str = str(verdict_val).strip().upper()
                if any(
                    x in v_str
                    for x in ("NOT_EQUIVALENT", "NOT EQUIVALENT", "FALSE", "NO", "DIFFERENT")
                ):
                    val_dict["verdict"] = "NOT_EQUIVALENT"
                elif any(x in v_str for x in ("EQUIVALENT", "TRUE", "YES", "IDENTICAL", "SAME")):
                    val_dict["verdict"] = "EQUIVALENT"
                else:
                    val_dict["verdict"] = "EQUIVALENT"
            else:
                val_dict["verdict"] = "EQUIVALENT"

            # 5. Normalize missing_operational_facts
            missing_val = val_dict.get("missing_operational_facts")
            if missing_val is None or not isinstance(missing_val, list):
                val_dict["missing_operational_facts"] = []
            else:
                val_dict["missing_operational_facts"] = [str(x) for x in missing_val]

            # 6. Normalize change_type
            if val_dict["verdict"] == "EQUIVALENT":
                val_dict["change_type"] = "EQUIVALENT"
            else:
                change_val = val_dict.get("change_type")
                if change_val is None:
                    for alias in ("origin", "change", "type", "regression_type", "conflict_type"):
                        if alias in val_dict and val_dict[alias] is not None:
                            change_val = val_dict[alias]
                            break
                if change_val is not None:
                    c_str = str(change_val).strip().upper()
                    if "CONFLICT" in c_str:
                        val_dict["change_type"] = "GENERATION_CONFLICT"
                    elif "AMBIGUOUS" in c_str:
                        val_dict["change_type"] = "AMBIGUOUS_CHANGE"
                    else:
                        val_dict["change_type"] = "GENERATOR_REGRESSION"
                else:
                    val_dict["change_type"] = "GENERATOR_REGRESSION"

        return values


@dataclasses.dataclass
class TextCandidate:
    """Dataclass representing a candidate pair of mismatched text fields to be evaluated."""

    entry_path: str
    baseline_text: str
    test_text: str


@dataclasses.dataclass
class JudgeEvaluationResult:
    """Dataclass holding the evaluated verdict for a text candidate."""

    entry_path: str
    baseline_text: str
    test_text: str
    verdict: JudgeVerdict


def create_judge_prompt(candidate: TextCandidate) -> str:
    """Construct prompt for semantic evaluation of two text fields.

    Args:
        candidate: TextCandidate containing baseline and test string.

    Returns:
        str: Formatted evaluation prompt for Gemini Judge.

    """
    return f"""Evaluate whether these two text fields are semantically equivalent:

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
        config.use_thinking = False
        config.temperature = 0.0
        llm = Gemini(config)
        close_after = True
    else:
        llm.config.use_thinking = False
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

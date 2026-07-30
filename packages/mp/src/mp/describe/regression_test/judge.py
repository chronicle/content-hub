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
    "You are an expert quality assurance evaluator and semantic judge. Your task is to determine if two text fields "
    "(which are parts of generated responses) are semantically equivalent with respect to answering a specific "
    "original user prompt.\n\n"
    "### Evaluation Criteria\n\n"
    "You must evaluate whether Text Field 1 and Text Field 2 are **semantically equal**.\n\n"
    "- **EQUIVALENT**: Both text fields convey the exact same core answer, factual claims, or decision.\n"
    "- *Ignore*: Minor grammatical differences, syntax, Markdown formatting (e.g., bullet points vs. paragraphs),\n"
    "tone, and verbosity (one field being longer or having more polite/explanatory fluff than the other). "
    "If the core answer is identical, they are EQUIVALENT.\n"
    "- **NOT_EQUIVALENT**: The two fields convey different facts, contradictory conclusions, or one field contains "
    "critical, prompt-relevant details or constraints that the other completely omits.\n\n"
    "### Rules for Borderline Cases & Supplementary Notes\n\n"
    "1. **Supplementary Notes / Additional Phrasing**: Differences in phrasing of supplementary notes (e.g. saying "
    "'does not process entities' vs 'does not require action parameters', or minor phrasing in flow steps) are NOT "
    "regressions. Do NOT mark NOT_EQUIVALENT unless there is a genuine factual contradiction or an omission of a "
    "critical operational mechanism (such as retries, rate limits, or required authentication keys).\n"
    "2. **Tie-Breaker Rule**: When two descriptions agree on the primary purpose, API endpoints, and general flow, "
    "but differ only in supplementary fluff or secondary notes, you MUST default to **EQUIVALENT**.\n\n"
    "### Step-by-Step Evaluation Protocol\n\n"
    "1. **Analyze the Prompt**: Identify the core information, decision, or question expected to be answered.\n"
    "2. **Deconstruct Field 1**: Extract essential semantic claims/facts present in Text Field 1.\n"
    "3. **Deconstruct Field 2**: Extract essential semantic claims/facts present in Text Field 2.\n"
    "4. **Map & Compare**: Contrast extracted claims. Are they functionally and semantically identical? "
    "Identify any critical omissions or contradictions.\n"
    "5. **Formulate the Verdict**: Make your final categorical determination based strictly on your mapping.\n"
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
    comparison_reasoning: str = Field(
        default="",
        description="A step-by-step logical comparison explaining why the core meanings are identical or different.",
    )
    verdict: Literal["EQUIVALENT", "NOT_EQUIVALENT"] = Field(
        default="EQUIVALENT",
        description="Categorical determination: EQUIVALENT or NOT_EQUIVALENT.",
    )

    @model_validator(mode="before")
    @classmethod
    def _map_aliases_and_defaults(  # ruff:ignore[complex-structure,too-many-branches]
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

import asyncio
import json
import logging
import pathlib
from datetime import datetime, timezone
from typing import Any, TypeVar

from mp.core.llm.gemini import Gemini, GeminiConfig
from mp.describe.action.agent_config import AgentConfig, ValidationResult
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T_Schema = TypeVar("T_Schema", bound=BaseModel)


class FieldAgent:
    def __init__(self, config: AgentConfig):
        self.config = config

    async def _draft(
        self, prompt_text: str, gemini: Gemini, target_model: type[T_Schema], max_api_retries: int = 3
    ) -> T_Schema | str:
        last_error = None
        for attempt in range(max_api_retries):
            try:
                return await gemini.send_message(
                    prompt_text, raise_error_if_empty_response=True, response_json_schema=target_model
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Draft API attempt {attempt + 1}/{max_api_retries} failed for {self.config.field_name}: {e}"
                )
                if attempt < max_api_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

        # Fallback text generation if structured output failed after retries
        try:
            raw_text = await gemini.send_message(
                prompt_text, raise_error_if_empty_response=True, response_json_schema=None
            )
            if isinstance(raw_text, str) and hasattr(target_model, "model_fields"):
                if self.config.field_name in target_model.model_fields:
                    return target_model(**{self.config.field_name: raw_text.strip()})
        except Exception as inner_e:
            logger.error(f"Fallback text generation also failed for {self.config.field_name}: {inner_e}")

        logger.error(
            f"Failed to generate draft for {self.config.field_name} after {max_api_retries} attempts: {last_error}"
        )
        return str(last_error)

    async def _validate(
        self, prompt_text: str, drafted_content: str, gemini: Gemini, max_api_retries: int = 3
    ) -> ValidationResult:
        prompt = f"""
    You are an extremely strict technical reviewer. You are evaluating drafted {self.config.field_name}.
    
    Action Information (Ground Truth Settings context for prompt):
    {prompt_text}
    
    Drafted Content:
    {drafted_content}
    
    Please evaluate the Drafted Content against the following rigorous checks:
    {self.config.validation_questions}
    
    If ANY of these fail, mark `is_valid` as False and provide explicit feedback.
    """
        last_error = None
        for attempt in range(max_api_retries):
            try:
                return await gemini.send_message(
                    prompt, raise_error_if_empty_response=True, response_json_schema=ValidationResult
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Validation API attempt {attempt + 1}/{max_api_retries} failed for {self.config.field_name}: {e}"
                )
                if attempt < max_api_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

        logger.error(
            f"Validation step failed for {self.config.field_name} after {max_api_retries} attempts: {last_error}"
        )
        return ValidationResult(is_valid=False, feedback=f"System error during validation: {last_error}")

    async def generate(self, prompt_text: str, target_model: type[T_Schema], context: dict) -> T_Schema | str:
        gemini_config = GeminiConfig(model_name=self.config.model_name, temperature=self.config.temperature)

        async with Gemini(config=gemini_config) as gemini:
            logger.info(f"Agent [{self.config.field_name}]: {self.config.draft_log_msg}")

            draft_obj = await self._draft(prompt_text, gemini, target_model)
            if isinstance(draft_obj, str):
                return draft_obj

            first_suggested_value = getattr(draft_obj, self.config.field_name, "")
            draft_content = first_suggested_value

            feedbacks = []
            final_value = first_suggested_value

            for attempt in range(self.config.max_retries):
                logger.info(
                    f"Agent [{self.config.field_name}]: Validating draft (Attempt {attempt + 1}/{self.config.max_retries})..."
                )
                validation: ValidationResult = await self._validate(prompt_text, str(draft_content), gemini)

                if validation.is_valid:
                    logger.info(
                        f"Agent [{self.config.field_name}]: Draft passed all validation checks. Submitting final response."
                    )
                    final_value = getattr(draft_obj, self.config.field_name, "")
                    break

                feedbacks.append(f"Attempt {attempt + 1} Failure: {validation.feedback}")
                logger.info(f"Agent [{self.config.field_name}]: Validation failed with feedback: {validation.feedback}")
                logger.info(f"Agent [{self.config.field_name}]: {self.config.refine_log_msg}")

                refinement_prompt = f"""
    Your previous output for {self.config.field_name} failed the validation checks.
    
    Previous Output:
    {draft_content}
    
    Feedback from Reviewer:
    {validation.feedback}
    
    Please rewrite the object, ensuring the \x27{self.config.field_name}\x27 fixes these issues.
    """
                draft_obj = await self._draft(refinement_prompt, gemini, target_model)
                if isinstance(draft_obj, str):
                    return draft_obj
                draft_content = getattr(draft_obj, self.config.field_name, "")
                final_value = draft_content
            else:
                logger.warning(
                    f"Agent [{self.config.field_name}]: Reached maximum retries. Returning last drafted content."
                )

            # Generate Report
            try:
                def _format_value(val: Any) -> str:
                    if hasattr(val, "model_dump_json"):
                        return val.model_dump_json(indent=2)
                    if hasattr(val, "model_dump"):
                        return json.dumps(val.model_dump(), indent=2)
                    return str(val)

                def _serialize_for_ledger(val: Any) -> Any:
                    if hasattr(val, "model_dump"):
                        return val.model_dump()
                    return val

                report_lines = [
                    f"Integration: {context.get('integration', 'Unknown')}",
                    f"Action: {context.get('action', 'Unknown')}",
                    f"Version: {context.get('version', 'Unknown')}",
                    f"Field: {self.config.field_name}",
                    "---",
                    f"First Suggested Value:\n{_format_value(first_suggested_value)}",
                    "---",
                    f"Reasoning for Validation Failure:\n"
                    + ("\n".join(feedbacks) if feedbacks else "None - Validated on first attempt without failures."),
                    "---",
                    f"Final Change and Setting:\n{_format_value(final_value)}",
                ]

                report_dir = pathlib.Path("agent_reports")
                report_dir.mkdir(exist_ok=True)
                report_path = (
                    report_dir
                    / f"{context.get('integration', 'Unknown')}_{context.get('action', 'Unknown')}_{self.config.field_name}.txt"
                )
                report_path.write_text("\n".join(report_lines))
                logger.info(f"Agent [{self.config.field_name}]: Report generated at {report_path}")

                # Generate JSONL Metrics Ledger
                metric = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "integration": str(context.get("integration", "Unknown")),
                    "action": str(context.get("action", "Unknown")),
                    "version": str(context.get("version", "Unknown")),
                    "field": self.config.field_name,
                    "required_refinement": bool(len(feedbacks) > 0),
                    "attempts_taken": len(feedbacks) + 1
                    if len(feedbacks) < self.config.max_retries
                    else self.config.max_retries,
                    "validation_feedbacks": feedbacks,
                    "first_suggested_value": _serialize_for_ledger(first_suggested_value),
                    "final_value": _serialize_for_ledger(final_value),
                }
                ledger_path = report_dir / "agent_metrics_ledger.jsonl"
                with open(ledger_path, "a") as ledger_file:
                    ledger_file.write(json.dumps(metric, default=str) + "\n")

            except Exception as e:
                logger.error(f"Failed to generate feedback log report: {e}")

            return draft_obj

    async def generate_bulk(
        self, prompts: list[str], target_model: type[T_Schema], contexts: list[dict] = None
    ) -> list[T_Schema | str]:
        if contexts is None:
            contexts = [{} for _ in prompts]
        semaphore = asyncio.Semaphore(3)

        async def _bounded_generate(p: str, ctx: dict):
            async with semaphore:
                return await self.generate(p, target_model, ctx)

        tasks = [_bounded_generate(p, ctx) for p, ctx in zip(prompts, contexts)]
        return await asyncio.gather(*tasks)

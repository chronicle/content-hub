import asyncio
import logging
from typing import Annotated, TypeVar

from pydantic import BaseModel, Field

from mp.core.llm.gemini import Gemini, GeminiConfig

logger = logging.getLogger(__name__)

GEMINI_MODEL_NAME = "gemini-3.1-pro-preview"
GEMINI_TEMPERATURE = 0.1

VALIDATION_QUESTIONS = """
1. Does the parameters table exclusively list the action-specific parameters defined in the JSON file?
2. Does the AI successfully avoid leaking any Integration-level parameters (like API, base URL or others)?
3. For every single parameter listed in the generated markdown table, does an exact, corresponding parameter definition exist in the provided JSON settings file?
4. If the original action has zero parameters defined, did the AI output the exact string: 'There are no parameters for this action' instead of a table?
5. Is the parameters description formatted precisely as a Markdown table with exactly these four column headers: | Parameter | Type | Mandatory | Description |?
6. Does the parameters description table document every single action-specific parameter declared in the provided JSON settings file, ensuring that zero required or optional action parameters are omitted from the Markdown table?
7. For every parameter listed in the Markdown table where the underlying JSON settings file or Python script defines a default value, enum choices, or specific formatting rules (such as CSV lists or integer ranges), are those default values and constraints explicitly stated in the Description column?
8. If the Python script or parameter metadata enforces conditional dependencies between parameters (e.g. 'Either Parameter A or Parameter B must be configured'), is this dependency explicitly documented within the specific parameter row description or notes?
"""


class ValidationResult(BaseModel):
    is_valid: Annotated[
        bool,
        Field(description="True if the parameters description successfully passes all 8 validation checks.")
    ]
    feedback: Annotated[
        str,
        Field(description="If is_valid is False, provide a detailed explanation of which questions failed and actionable steps to fix them. Start with checking each of the 8 validation questions.")
    ]

T_Schema = TypeVar("T_Schema", bound=BaseModel)

async def _draft_parameter_description(prompt_text: str, gemini: Gemini, target_model: type[T_Schema]) -> T_Schema | str:
    """Uses LLM to generate the initial draft of the parameter table."""
    try:
        response = await gemini.send_message(prompt_text, raise_error_if_empty_response=True, response_json_schema=target_model)
        return response
    except Exception as e:
        logger.error(f"Failed to generate draft parameter description: {e}")
        return str(e)


async def _validate_description(prompt_text: str, drafted_content: str, gemini: Gemini) -> ValidationResult:
    """Uses LLM to validate the draft against the predefined questions."""
    prompt = f"""
    You are an extremely strict technical reviewer. You are evaluating a drafted parameters description table.
    
    Action Information (Ground Truth Settings context for prompt):
    {prompt_text}
    
    Drafted Parameters Description:
    {drafted_content}
    
    Please evaluate the Drafted Parameters Description against the following 8 rigorous checks:
    {VALIDATION_QUESTIONS}
    
    If ANY of these fail (e.g. a parameter is missing, headers are wrong, defaults missing), mark `is_valid` as False and provide explicit feedback.
    """
    
    try:
        response = await gemini.send_message(prompt, raise_error_if_empty_response=True, response_json_schema=ValidationResult)
        return response
    except Exception as e:
        logger.error(f"Validation step failed: {e}")
        return ValidationResult(is_valid=False, feedback=f"System error during validation: {e}")


async def generate_validated_parameters_description(prompt_text: str, target_model: type[T_Schema], max_retries: int = 3) -> T_Schema | str:
    """
    Orchestrator loop working on a single prompt.
    """
    config = GeminiConfig(model_name=GEMINI_MODEL_NAME, temperature=GEMINI_TEMPERATURE)
    
    async with Gemini(config=config) as gemini:
        # Step 1: Draft
        logger.info("Agent: Generating initial parameter description draft...")
        draft_obj: T_Schema | str = await _draft_parameter_description(prompt_text, gemini, target_model)
        if isinstance(draft_obj, str):
            return draft_obj
            
        draft_content = getattr(draft_obj, "parameters_description", "")
        
        # Step 2 & 3: Validate and Self-Correct Loop
        for attempt in range(max_retries):
            logger.info(f"Agent: Validating draft (Attempt {attempt + 1}/{max_retries})...")
            validation: ValidationResult = await _validate_description(prompt_text, draft_content, gemini)
            
            if validation.is_valid:
                logger.info("Agent: Draft passed all validation checks. Submitting final table.")
                return draft_obj
            
            logger.info(f"Agent: Validation failed with feedback: {validation.feedback}")
            logger.info("Agent: Refning draft based on feedback...")
            
            refinement_prompt = f"""
            Your previous output for the parameters description failed the validation checks.
            
            Previous Output:
            {draft_content}
            
            Feedback from Reviewer:
            {validation.feedback}
            
            Please rewrite the object, ensuring the 'parameters_description' fixes these issues.
            """
            draft_obj = await _draft_parameter_description(refinement_prompt, gemini, target_model)
            if isinstance(draft_obj, str):
                return draft_obj
            draft_content = getattr(draft_obj, "parameters_description", "")
            
        logger.warning("Agent: Reached maximum retries. Returning last drafted description.")
        return draft_obj

async def generate_validated_parameters_description_bulk(prompts: list[str], target_model: type[T_Schema]) -> list[T_Schema | str]:
    """Provides a bulk interface to run our agent on multiple resources concurrently."""
    tasks = [generate_validated_parameters_description(p, target_model) for p in prompts]
    return await asyncio.gather(*tasks)

import asyncio
import logging
from typing import Annotated, TypeVar

from pydantic import BaseModel, Field

from mp.core.llm.gemini import Gemini, GeminiConfig

logger = logging.getLogger(__name__)

class ValidationResult(BaseModel):
    is_valid: Annotated[
        bool,
        Field(description="True if the output successfully passes all validation checks.")
    ]
    feedback: Annotated[
        str,
        Field(description="If is_valid is False, provide a detailed explanation of which questions failed and actionable steps to fix them. Start with checking each validation question.")
    ]

T_Schema = TypeVar("T_Schema", bound=BaseModel)

class AgentConfig(BaseModel):
    field_name: str
    validation_questions: str
    model_name: str = "gemini-3.1-pro-preview"
    temperature: float = 0.1
    max_retries: int = 3
    draft_log_msg: str = "Generating initial draft..."
    refine_log_msg: str = "Refining draft based on feedback..."

class FieldAgent:
    def __init__(self, config: AgentConfig):
        self.config = config

    async def _draft(self, prompt_text: str, gemini: Gemini, target_model: type[T_Schema]) -> T_Schema | str:
        try:
            return await gemini.send_message(prompt_text, raise_error_if_empty_response=True, response_json_schema=target_model)
        except Exception as e:
            logger.error(f"Failed to generate draft for {self.config.field_name}: {e}")
            return str(e)

    async def _validate(self, prompt_text: str, drafted_content: str, gemini: Gemini) -> ValidationResult:
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
        try:
            return await gemini.send_message(prompt, raise_error_if_empty_response=True, response_json_schema=ValidationResult)
        except Exception as e:
            logger.error(f"Validation step failed for {self.config.field_name}: {e}")
            return ValidationResult(is_valid=False, feedback=f"System error during validation: {e}")

    async def generate(self, prompt_text: str, target_model: type[T_Schema]) -> T_Schema | str:
        gemini_config = GeminiConfig(model_name=self.config.model_name, temperature=self.config.temperature)
        
        async with Gemini(config=gemini_config) as gemini:
            logger.info(f"Agent [{self.config.field_name}]: {self.config.draft_log_msg}")
            
            draft_obj = await self._draft(prompt_text, gemini, target_model)
            if isinstance(draft_obj, str):
                return draft_obj
                
            draft_content = getattr(draft_obj, self.config.field_name, "")
            
            for attempt in range(self.config.max_retries):
                logger.info(f"Agent [{self.config.field_name}]: Validating draft (Attempt {attempt + 1}/{self.config.max_retries})...")
                validation: ValidationResult = await self._validate(prompt_text, str(draft_content), gemini)
                
                if validation.is_valid:
                    logger.info(f"Agent [{self.config.field_name}]: Draft passed all validation checks. Submitting final response.")
                    return draft_obj
                
                logger.info(f"Agent [{self.config.field_name}]: Validation failed with feedback: {validation.feedback}")
                logger.info(f"Agent [{self.config.field_name}]: {self.config.refine_log_msg}")
                
                refinement_prompt = f"""
    Your previous output for {self.config.field_name} failed the validation checks.
    
    Previous Output:
    {draft_content}
    
    Feedback from Reviewer:
    {validation.feedback}
    
    Please rewrite the object, ensuring the '{self.config.field_name}' fixes these issues.
    """
                draft_obj = await self._draft(refinement_prompt, gemini, target_model)
                if isinstance(draft_obj, str):
                    return draft_obj
                draft_content = getattr(draft_obj, self.config.field_name, "")
                
            logger.warning(f"Agent [{self.config.field_name}]: Reached maximum retries. Returning last drafted content.")
            return draft_obj

    async def generate_bulk(self, prompts: list[str], target_model: type[T_Schema]) -> list[T_Schema | str]:
        tasks = [self.generate(p, target_model) for p in prompts]
        return await asyncio.gather(*tasks)

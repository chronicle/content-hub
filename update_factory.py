import re

with open("packages/mp/src/mp/describe/action/agent_factory.py", "r") as f:
    code = f.read()

# Add context to generate
code = code.replace(
    'async def generate(self, prompt_text: str, target_model: type[T_Schema]) -> T_Schema | str:',
    'async def generate(self, prompt_text: str, target_model: type[T_Schema], context: dict) -> T_Schema | str:'
)

# Replace generate body
new_body = """        gemini_config = GeminiConfig(model_name=self.config.model_name, temperature=self.config.temperature)
        
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
                logger.info(f"Agent [{self.config.field_name}]: Validating draft (Attempt {attempt + 1}/{self.config.max_retries})...")
                validation: ValidationResult = await self._validate(prompt_text, str(draft_content), gemini)
                
                if validation.is_valid:
                    logger.info(f"Agent [{self.config.field_name}]: Draft passed all validation checks. Submitting final response.")
                    final_value = getattr(draft_obj, self.config.field_name, "")
                    break
                
                feedbacks.append(f"Attempt {attempt + 1} Failure: {validation.feedback}")
                logger.info(f"Agent [{self.config.field_name}]: Validation failed with feedback: {validation.feedback}")
                logger.info(f"Agent [{self.config.field_name}]: {self.config.refine_log_msg}")
                
                refinement_prompt = f\"\"\"
    Your previous output for {self.config.field_name} failed the validation checks.
    
    Previous Output:
    {draft_content}
    
    Feedback from Reviewer:
    {validation.feedback}
    
    Please rewrite the object, ensuring the '{self.config.field_name}' fixes these issues.
    \"\"\"
                draft_obj = await self._draft(refinement_prompt, gemini, target_model)
                if isinstance(draft_obj, str):
                    return draft_obj
                draft_content = getattr(draft_obj, self.config.field_name, "")
                final_value = draft_content
            else:
                logger.warning(f"Agent [{self.config.field_name}]: Reached maximum retries. Returning last drafted content.")
            
            # Generate Report
            try:
                import pathlib
                report_lines = [
                    f"Integration: {context.get('integration', 'N/A')}",
                    f"Action: {context.get('action', 'N/A')}",
                    f"Version: {context.get('version', 'N/A')}",
                    f"Field: {self.config.field_name}",
                    "---",
                    f"First Suggested Value:\\n{first_suggested_value}",
                    "---",
                    f"Reasoning for Validation Failure:\\n" + ("\\n".join(feedbacks) if feedbacks else "None - Validated on first attempt without failures."),
                    "---",
                    f"Final Change and Setting:\\n{final_value}"
                ]
                report_dir = pathlib.Path("agent_reports")
                report_dir.mkdir(exist_ok=True)
                report_path = report_dir / f"{context.get('integration', 'Unknown')}_{context.get('action', 'Unknown')}_{self.config.field_name}.txt"
                report_path.write_text("\\n".join(report_lines))
                logger.info(f"Agent [{self.config.field_name}]: Report generated at {report_path}")
            except Exception as e:
                logger.error(f"Failed to generate feedback log report: {e}")
                
            return draft_obj"""

import re
code = re.sub(r'        gemini_config = GeminiConfig\(model_name=self\.config\.model_name, temperature=self\.config\.temperature\).*?return draft_obj', new_body, code, flags=re.DOTALL)

code = code.replace(
    'async def generate_bulk(self, prompts: list[str], target_model: type[T_Schema]) -> list[T_Schema | str]:',
    'async def generate_bulk(self, prompts: list[str], target_model: type[T_Schema], contexts: list[dict] = None) -> list[T_Schema | str]:\n        if contexts is None: contexts = [{} for _ in prompts]'
)
code = code.replace(
    'tasks = [self.generate(p, target_model) for p in prompts]',
    'tasks = [self.generate(p, target_model, ctx) for p, ctx in zip(prompts, contexts)]'
)

with open("packages/mp/src/mp/describe/action/agent_factory.py", "w") as f:
    f.write(code)


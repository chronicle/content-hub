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

from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from ..core.VertexAIApiManager import ApiManager
from ..core.VertexAIBaseAction import BaseAction
from ..core.VertexAIConstants import (
    EXECUTE_PROMPT_SCRIPT_NAME,
)
from ..core.VertexAIDatamodels import GenerationConfig, Prompt
from ..core.VertexAIExceptions import VertexAIValidationException
from ..core.VertexAIUtils import get_publisher_name

SUCCESS_MESSAGE = "Successfully executed a prompt."
PROMPT_COUNT_EXCEEDED = (
    "exceeded the maximum input token threshold. Adjust the configuration of the "
    "action."
)


class ExecutePrompt(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self._api_client: ApiManager | None = None
        self.json_results = None

    def _extract_parameters(self) -> None:
        """Extract action parameters."""
        self.params.model_id = extract_action_param(
            self.soar_action,
            param_name="Model ID",
            print_value=True,
        )
        self.params.publisher_name = extract_action_param(
            self.soar_action,
            param_name="Publisher Name",
            print_value=True,
        )
        self.params.text_prompt = extract_action_param(
            self.soar_action,
            param_name="Text Prompt",
            print_value=True,
        )
        self.params.temperature = extract_action_param(
            self.soar_action,
            param_name="Temperature",
            print_value=True,
        )
        self.params.candidate_count = extract_action_param(
            self.soar_action,
            param_name="Candidate Count",
            print_value=True,
        )
        self.params.response_mime_type = extract_action_param(
            self.soar_action,
            param_name="Response MIME type",
            print_value=True,
        )
        self.params.response_schema = extract_action_param(
            self.soar_action,
            param_name="Response Schema",
            print_value=True,
        )
        self.params.max_input_tokens = extract_action_param(
            self.soar_action,
            param_name="Max Input Tokens",
            print_value=True,
        )
        self.params.max_output_tokens = extract_action_param(
            self.soar_action,
            param_name="Max Output Tokens",
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate action parameters."""
        super()._validate_params()
        validator = ParameterValidator(self.soar_action)

        if not is_empty_string_or_none(self.params.temperature):
            self.params.temperature = validator.validate_float(
                param_name="Temperature",
                value=self.params.temperature,
                print_value=True,
            )
        if not is_empty_string_or_none(self.params.candidate_count):
            self.params.candidate_count = validator.validate_float(
                param_name="Candidate Count",
                value=self.params.candidate_count,
                print_value=True,
            )
        if not is_empty_string_or_none(self.params.response_schema):
            self.params.response_schema = validator.validate_json(
                param_name="Response Schema",
                json_string=self.params.response_schema,
                print_value=True,
            )
        self.params.response_mime_type = validator.validate_ddl(
            param_name="Response MIME type",
            value=self.params.response_mime_type,
            ddl_values=["application/json", "text/plain", "text/x.enum"],
            print_value=True,
        )
        if not is_empty_string_or_none(self.params.max_input_tokens):
            self.params.max_input_tokens = validator.validate_positive(
                param_name="Max Input Tokens",
                value=self.params.max_input_tokens,
                print_value=True,
            )
        if not is_empty_string_or_none(self.params.max_output_tokens):
            self.params.max_output_tokens = validator.validate_positive(
                param_name="Max Output Tokens",
                value=self.params.max_output_tokens,
                print_value=True,
            )

    def _perform_action(self, _=None) -> None:
        prompt = Prompt(text=self.params.text_prompt)
        generation_config = GenerationConfig(
            temperature=self.params.temperature,
            candidate_count=self.params.candidate_count,
            max_output_tokens=self.params.max_output_tokens,
            response_mime_type=self.params.response_mime_type,
            response_schema=self.params.response_schema,
        )
        publisher_name = get_publisher_name(
            input_publisher_name=self.params.publisher_name,
            default_publisher=self.params.default_publisher_name,
        )
        if self.params.max_input_tokens:
            token_count = self.api_client.count_tokens(
                model_id=self.params.model_id or self.params.default_model,
                prompt=prompt,
                publisher_name=publisher_name,
                generation_config=generation_config,
            )
            if token_count > self.params.max_input_tokens:
                raise VertexAIValidationException(PROMPT_COUNT_EXCEEDED)

        generation_result = self.api_client.generate_content(
            self.params.model_id or self.params.default_model,
            prompt,
            publisher_name,
            generation_config,
            max_output_tokens=self.params.max_output_tokens,
        )
        self.json_results = generation_result.to_json()


def main() -> None:
    ExecutePrompt(EXECUTE_PROMPT_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

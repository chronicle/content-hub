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

import base64

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_dict_to_json_result_dict
from TIPCommon.types import Entity
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from vertex_ai.core.VertexAIApiManager import ApiManager
from vertex_ai.core.VertexAIBaseAction import BaseAction
from vertex_ai.core.VertexAIConstants import ANALYZE_EML_SCRIPT_NAME
from vertex_ai.core.VertexAIDatamodels import (
    GenerationConfig,
    GenerationResult,
    Prompt,
)
from vertex_ai.core.VertexAIExceptions import VertexAIValidationException
from vertex_ai.core.VertexAIUtils import get_publisher_name

SUCCESS_MESSAGE = "Successfully analysed the following EML files using Vertex AI: {}.\n"
NOT_FOUND_FILES = "The following files were not found: {}."
NO_FILES_FOUND = "None of the provided files were found."

EXPLAIN_ENTITY_PROMPT = (
    "You are a Security Analyst. Analyze the content of a base64 encoded EML file for "
    "security risks, including phishing links, suspicious attachments, and social "
    "engineering tactics. Provide a concise analysis summary (maximum 75 words) and a "
    "JSON object with these fields: threat_level (Critical, High, Medium, Low, None), "
    "threats_found (list of strings containing information about threats with "
    "explanations and specific examples from the email), verification_steps (list of "
    "strings specifying steps and tools to verify risks), and protection_measures (list"
    " of strings for security measures to protect against the identified threats). "
    "Rank identified threats by severity. Base your analysis solely on the provided "
    "EML file; do not use styling or bullet points. If no immediate threats are "
    'found, state "No immediate threats detected, but further analysis may be '
    'required" with justification.'
)


class AnalyzeEML(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self._api_client: ApiManager | None = None
        self.json_results = {}
        self.result_value = False

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
        self.params.temperature = extract_action_param(
            self.soar_action,
            param_name="Temperature",
            print_value=True,
        )
        self.params.files_to_analyze = extract_action_param(
            self.soar_action, param_name="Files To Analyze", print_value=True,
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

        self.params.files_list = validator.validate_csv(
            param_name="Files To Analyze",
            csv_string=self.params.files_to_analyze,
        )
        if not is_empty_string_or_none(self.params.temperature):
            self.params.temperature = validator.validate_float(
                param_name="Temperature",
                value=self.params.temperature,
            )
        if not is_empty_string_or_none(self.params.max_output_tokens):
            self.params.max_output_tokens = validator.validate_positive(
                param_name="Max Output Tokens",
                value=self.params.max_output_tokens,
            )

    def _generate_file_analysis(
        self,
        file_name: str,
    ) -> GenerationResult:
        """Generate new file analysis."""
        with open(file_name, "rb") as input_file:
            content_data = base64.b64encode(input_file.read()).decode("utf-8")
            prompt = Prompt(
                text=EXPLAIN_ENTITY_PROMPT,
                inline_data=[{"mimeType": "text/plain", "data": content_data}],
            )

        generation_config = GenerationConfig(
            temperature=self.params.temperature,
            response_mime_type="application/json",
            max_output_tokens=self.params.max_output_tokens,
        )
        publisher_name = get_publisher_name(
            input_publisher_name=self.params.publisher_name,
            default_publisher=self.params.default_publisher_name,
        )
        generation_result = self.api_client.generate_content(
            model_id=self.params.model_id or self.params.default_model,
            prompt=prompt,
            publisher_name=publisher_name,
            generation_config=generation_config,
            content_data=content_data,
            max_output_tokens=self.params.max_output_tokens,
        )
        return generation_result

    def _perform_action(self, _: Entity | None) -> None:
        analysed_files = []
        not_found_files = []
        json_results = {}

        for file_name in self.params.files_list:
            try:
                analysis = self._generate_file_analysis(file_name)
                result_ = {
                    "raw": analysis.text_content,
                    "extracted_info": analysis.json_content,
                    "usageMetadata": analysis.usage_metadata,
                }
                json_results[file_name] = result_
                analysed_files.append(file_name)

            except FileNotFoundError:
                self.logger.error(f"File {file_name} not found")
                not_found_files.append(file_name)

        if not analysed_files:
            raise VertexAIValidationException(NO_FILES_FOUND)

        self.json_results = convert_dict_to_json_result_dict(json_results)
        self.output_message += SUCCESS_MESSAGE.format(", ".join(analysed_files))
        self.result_value = True

        if not_found_files:
            self.output_message += NOT_FOUND_FILES.format(", ".join(not_found_files))


def main() -> None:
    AnalyzeEML(ANALYZE_EML_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

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
import json

from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from vertex_ai.core.VertexAIApiManager import ApiManager
from vertex_ai.core.VertexAIBaseAction import BaseAction
from vertex_ai.core.VertexAIConstants import TRANSFORM_DATA_SCRIPT_NAME
from vertex_ai.core.VertexAIDatamodels import (
    GenerationConfig,
    Prompt,
)
from vertex_ai.core.VertexAIUtils import get_publisher_name

SUCCESS_MESSAGE = "Successfully transformed provided data."


class TransformData(BaseAction):
    def __init__(self) -> None:
        super().__init__(TRANSFORM_DATA_SCRIPT_NAME)
        self.output_message = SUCCESS_MESSAGE
        self._api_client: ApiManager | None = None
        self.json_results = {}

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
        self.params.json_object = extract_action_param(
            self.soar_action,
            param_name="JSON Object",
            print_value=True,
        )
        self.params.temperature = extract_action_param(
            self.soar_action,
            param_name="Temperature",
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

        self.params.json_object = validator.validate_json(
            param_name="JSON Object",
            json_string=self.params.json_object,
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

    def _perform_action(self, _=None) -> None:
        content_data = base64.b64encode(
            json.dumps(self.params.json_object).encode("utf-8"),
        ).decode("utf-8")
        prompt = Prompt(
            text=self.params.text_prompt,
            inline_data=[{"mimeType": "text/plain", "data": content_data}],
        )
        generation_config = GenerationConfig(
            temperature=self.params.temperature,
            max_output_tokens=self.params.max_output_tokens,
            response_mime_type="application/json",
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
        self.json_results = generation_result.to_json()


def main() -> None:
    TransformData().run()


if __name__ == "__main__":
    main()

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

from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import get_entity_data
from TIPCommon.types import Entity, SingleJson
from TIPCommon.utils import get_entity_original_identifier, is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from ..core.VertexAIApiManager import ApiManager
from ..core.VertexAIBaseAction import BaseAction
from ..core.VertexAIConstants import DESCRIBE_ENTITY_SCRIPT_NAME
from ..core.VertexAIDatamodels import (
    GenerationCache,
    GenerationConfig,
    Prompt,
)
from ..core.VertexAIUtils import (
    exclude_fields_from_entity,
    flatten_entity_data_for_generation,
    get_publisher_name,
)

SUCCESS_MESSAGE = (
    "Successfully summarized the entity based on the available information using "
    "Vertex AI."
)

EXPLAIN_ENTITY_PROMPT = (
    "You are a Security Analyst. You will receive a JSON object containing metadata "
    "about a security entity (this could be an IP address, a file hash, etc.). Your "
    "task is to provide a concise summary of this entity metadata. Avoid remediation "
    "steps, styling, and bullet points. Only use information from the provided JSON "
    "object."
)


class DescribeEntity(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self._api_client: ApiManager | None = None
        self.json_results = {}
        self.result_value = False
        self._entity_types = list(EntityTypesEnum)

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
        self.params.exclude_fields = extract_action_param(
            self.soar_action, param_name="Exclude Fields", print_value=True,
        )
        self.params.force_refresh = extract_action_param(
            self.soar_action,
            input_type=bool,
            param_name="Force Refresh",
            print_value=True,
        )
        self.params.refresh_after = extract_action_param(
            self.soar_action, param_name="Refresh After (Days)", print_value=True,
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

        self.params.exclude_fields_list = validator.validate_csv(
            param_name="Exclude Fields",
            csv_string=self.params.exclude_fields,
        )
        self.params.refresh_after = validator.validate_positive(
            param_name="Refresh After (Days)",
            value=self.params.refresh_after,
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

    def _get_entity_summary(
        self,
        original_identifier: str,
        flattened_entity: SingleJson,
    ) -> tuple[str | list[str], SingleJson | str]:
        """Build entity summary."""
        entity_data = base64.b64encode(
            json.dumps(flattened_entity).encode("utf-8"),
        ).decode("utf-8")
        prompt = Prompt(
            text=EXPLAIN_ENTITY_PROMPT,
            inline_data=[{"mimeType": "text/plain", "data": entity_data}],
        )
        generation_config = GenerationConfig(
            temperature=self.params.temperature,
            max_output_tokens=self.params.max_output_tokens,
        )
        generation_cache = GenerationCache(
            self,
            environment=flattened_entity["entity"]["environment"],
            model_id=self.params.model_id or self.params.default_model,
            generation_config=generation_config,
        )
        cached_summary = self._get_entity_summary_cache(
            original_identifier,
            prompt,
            generation_cache,
        )
        if cached_summary is not None:
            return cached_summary, "Used cached summary."
        publisher_name = get_publisher_name(
            input_publisher_name=self.params.publisher_name,
            default_publisher=self.params.default_publisher_name,
        )

        generation_result = self.api_client.generate_content(
            model_id=self.params.model_id or self.params.default_model,
            prompt=prompt,
            publisher_name=publisher_name,
            generation_config=generation_config,
            content_data=entity_data,
            max_output_tokens=self.params.max_output_tokens,
        )
        generation_cache.save_summary(
            original_identifier,
            prompt,
            summary=generation_result.text_content,
        )
        return generation_result.text_content, generation_result.usage_metadata

    def _get_entity_summary_cache(
        self,
        original_identifier: str,
        prompt: Prompt,
        generation_cache: GenerationCache,
    ) -> str | None:
        """Retrieve entity summary cache."""
        if self.params.force_refresh:
            return None

        summary = generation_cache.get_cached_summary(
            original_identifier,
            prompt,
            refresh_after=self.params.refresh_after,
        )
        if summary is None:
            return None

        self.logger.info(
            f"Found cached generation for entity {original_identifier}, "
            "skipping generation ...",
        )
        return summary

    def _on_entity_failure(self, current_entity: Entity, error: Exception) -> None:
        raise error

    def _perform_action(self, current_entity: Entity | None) -> None:
        original_identifier = get_entity_original_identifier(current_entity)
        entity_data = get_entity_data(
            self.soar_action,
            entity_identifier=original_identifier,
            entity_type=current_entity.entity_type,
            entity_environment=current_entity.additional_properties["Environment"],
        )
        if entity_data["entity"] is None:
            self.logger.error(f"Entity {original_identifier} was not found!")
            return

        flattened_entity = flatten_entity_data_for_generation(entity_data)
        exclude_fields_from_entity(
            flattened_entity,
            keys=self.params.exclude_fields_list,
        )
        summary, usage_metadata = self._get_entity_summary(
            original_identifier, flattened_entity,
        )
        self.json_results[original_identifier] = {
            "summary": summary,
            "usageMetadata": usage_metadata,
        }
        self.result_value = True


def main() -> None:
    DescribeEntity(DESCRIBE_ENTITY_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()

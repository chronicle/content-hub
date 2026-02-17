# Copyright 2025 Google LLC
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

import json
import os
from collections.abc import Iterator
from contextlib import suppress
from typing import Any, Never, TypeAlias

import vertexai
from google.cloud.aiplatform_v1beta1.types import StreamQueryReasoningEngineRequest
from TIPCommon.extraction import extract_action_param
from vertexai.preview import reasoning_engines

from ..core import constants
from ..core.base_action import BaseAction

SCRIPT_NAME = "ServiceNow Agent"
AGENT_ID: str = "6615597637095653376"

JsonDict: TypeAlias = dict[str, Any]
AgentResponse: TypeAlias = JsonDict | list[JsonDict] | str | None


def main() -> None:
    ServiceNowAgent().run()


class ServiceNowAgent(BaseAction):
    def __init__(self) -> None:
        super().__init__(f"{constants.INTEGRATION_NAME} - {SCRIPT_NAME}")

    def _extract_action_parameters(self) -> None:
        self.params.prompt = extract_action_param(
            self.soar_action,
            param_name="Prompt",
            print_value=True,
        )
        self.params.agent_id = extract_action_param(
            self.soar_action,
            param_name="Agent ID",
            print_value=True,
        )
        self.params.project_id = extract_action_param(
            self.soar_action,
            param_name="GCP Project ID",
            print_value=True,
        )
        self.params.region = extract_action_param(
            self.soar_action,
            param_name="GCP Region",
            print_value=True,
        )
        self.params.user = extract_action_param(
            self.soar_action,
            param_name="User",
            print_value=True,
        )

    def _perform_action(self, _: Never) -> None:
        self._validate_project()
        self._validate_region()

        self.logger.info(
            "🔌 Connecting to agent: %s in %s/%s",
            self.params.agent_id,
            self.params.project_id,
            self.params.region,
        )
        vertexai.init(project=self.params.project_id, location=self.params.region)

        resource_name: str = self._get_resource_name()
        self.logger.info("🔍 Fetching agent: %s", resource_name)

        agent_engine = reasoning_engines.ReasoningEngine(resource_name)
        self.logger.info("💬 Sending prompt: '%s'", self.params.prompt)

        response_stream = self._send_request(agent_engine, resource_name)
        self.json_results = self._process_response_stream(response_stream)

    def _get_resource_name(self) -> str:
        """Construct the full resource name for the agent.

        Returns:
            The full resource name string.

        """
        if "/" not in self.params.agent_id:
            return (
                f"projects/{self.params.project_id}/"
                f"locations/{self.params.region}/"
                f"reasoningEngines/{self.params.agent_id}"
            )

        return self.params.agent_id

    def _send_request(
        self,
        agent_engine: reasoning_engines.ReasoningEngine,
        resource_name: str,
    ) -> Iterator[Any]:
        """Send the request to the agent engine and return the response stream.

        Returns:
            An iterator over the response chunks.

        """
        payload = {
            "message": {"role": "user", "parts": [{"text": self.params.prompt}]},
            "user_id": self.params.user,
        }
        request_json: str = json.dumps(payload)

        req = StreamQueryReasoningEngineRequest(
            name=resource_name,
            input={"request_json": request_json},
            class_method="streaming_agent_run_with_events",
        )

        return agent_engine.execution_api_client.stream_query_reasoning_engine(request=req)

    def _process_response_stream(self, response_stream: Iterator[Any]) -> AgentResponse:
        """Process the response stream and print the output.

        Returns:
            The parsed response from the stream.

        """
        self.logger.info("\n🤖 Response Stream:")
        collected_data = []

        for chunk in response_stream:
            if hasattr(chunk, "data") and chunk.data:
                try:
                    data_str = chunk.data.decode("utf-8")
                    self.logger.debug("Chunk received: %s", data_str)
                    collected_data.append(data_str)
                except UnicodeDecodeError:
                    self.logger.exception("Failed to decode chunk data: %s", chunk.data)

        if not collected_data:
            self.logger.warning("⚠️ No response chunks received!")
            return None

        full_response = "".join(collected_data)
        return self._parse_full_response(full_response)

    def _parse_full_response(self, full_response: str) -> AgentResponse:
        """Parse the full response string and log it.

        Returns:
            The parsed JSON objects or the raw response if parsing fails.

        """
        try:
            json_objects: list[JsonDict] = []
            decoder = json.JSONDecoder()
            pos = 0
            while pos < len(full_response):
                full_response_strip = full_response[pos:].strip()
                if not full_response_strip:
                    break

                while pos < len(full_response) and full_response[pos].isspace():
                    pos += 1

                if pos >= len(full_response):
                    break

                try:
                    obj, idx = decoder.raw_decode(full_response[pos:])
                    json_objects.append(obj)
                    pos += idx
                except json.JSONDecodeError:
                    break

            if len(json_objects) == 1:
                remainder: str = full_response[pos:].strip()
                if not remainder:
                    return json_objects[0]

            if json_objects:
                return {"response": json_objects}

            with suppress(json.JSONDecodeError):
                return json.loads(full_response)

        except (ValueError, TypeError) as e:  # Catching specific json/parsing errors
            self.logger.warning("Failed to parse response as JSON: %s", e)
            self.logger.info(json.dumps({"response": full_response}, indent=2))

        return full_response

    def _validate_project(self) -> None:
        project_id: str | None = (
            self.params.project_id
            or os.environ.get("DEPLOY_GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
        )
        if not project_id:
            msg = "DEPLOY_GOOGLE_CLOUD_PROJECT must be set or passed as an argument"
            self.logger.error(msg)
            raise ValueError(msg)

        self.params.project_id = project_id

    def _validate_region(self) -> None:
        region: str | None = (
            self.params.region
            or os.environ.get("DEPLOY_GOOGLE_CLOUD_REGION")
            or os.environ.get("GOOGLE_CLOUD_REGION")
        )
        if not region:
            msg = "DEPLOY_GOOGLE_CLOUD_REGION must be set or passed as an argument"
            self.logger.error(msg)
            raise ValueError(msg)

        self.params.region = region


if __name__ == "__main__":
    main()

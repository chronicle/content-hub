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
from typing import Any, Literal, Never, TypeAlias, TypedDict

import vertexai
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from vertexai.agent_engines.templates.adk import AdkApp

from ..core import constants
from ..core.base_action import BaseAction


SCRIPT_NAME = "ServiceNow Agent"
AGENT_ID: str = "5020338206588010496"
USER_ID: str = "SecOps-123"

JsonDict: TypeAlias = dict[str, Any]
AgentResponse: TypeAlias = JsonDict | list[JsonDict] | str | None


class ToolCall(TypedDict):
    step: Literal["call"]
    tool: str
    args: dict[str, Any]


class ToolResponse(TypedDict):
    step: Literal["result"]
    tool: str
    output: Any


class AgentMetadata(TypedDict):
    tools_used: list[Any]
    usage: dict[str, int]
    event_count: int


class AgentExecutionResult(TypedDict):
    results: JsonDict | list[Any] | None
    metadata: AgentMetadata


def main() -> None:
    ServiceNowAgent().run()


class ServiceNowAgent(BaseAction):
    def __init__(self) -> None:
        super().__init__(f"{constants.INTEGRATION_NAME} - {SCRIPT_NAME}")

    def _extract_action_parameters(self) -> None:
        self.params.agent_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Agent ID",
            print_value=True,
        )
        self.params.project_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="GCP Project ID",
            print_value=True,
        )
        self.params.region = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="GCP Region",
            print_value=True,
        )

        self.params.prompt = extract_action_param(
            self.soar_action,
            param_name="Prompt",
            print_value=True,
        )
        json_schema: str = extract_action_param(
            self.soar_action,
            param_name="Response JSON Schema",
            print_value=True,
        )
        self.params.response_schema = json.loads(json_schema) if json_schema else None
        self.params.temperature = extract_action_param(
            self.soar_action,
            param_name="Model Temperature",
            print_value=True,
            input_type=float,
        )

    def _perform_action(self, _: Never) -> None:
        self.logger.info(
            "🔌 Connecting to agent: %s in %s/%s",
            self.params.agent_id,
            self.params.project_id,
            self.params.region,
        )
        vertexai.init(project=self.params.project_id, location=self.params.region)
        client = vertexai.Client(project=self.params.project_id, location=self.params.region)
        resource_name: str = self._get_resource_name()
        self.logger.info("🔍 Fetching agent: %s", resource_name)
        adk_app: AdkApp = client.agent_engines.get(name=resource_name)
        self.logger.info(
            "💬 Sending prompt: '%s' with config params: %s",
            self.params.prompt,
            self.params.agent_config_params,
        )

        events: list[JsonDict] = self._send_request(adk_app)
        self.json_results = self._parse_agent_events(events)

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

    def _send_request(self, adk_app: AdkApp) -> list[JsonDict]:
        """Send the request to the agent engine and return the response stream.

        Returns:
            An iterator over the response chunks.

        """
        s: str | None = self.params.response_schema
        schema: JsonDict | None = json.loads(s) if s is not None else None
        return list(
            adk_app.stream_query(
                message=self.params.prompt,
                user_id=USER_ID,
                run_config={
                    "response_schema": schema,
                    "temperature": self.params.temperature,
                },
            )
        )

    def _parse_agent_events(self, events: list[JsonDict]) -> AgentExecutionResult:
        final_result: JsonDict | None = None
        tools_executed: list[ToolCall | ToolResponse] = []
        usage_stats: JsonDict = {}

        for event in events:
            if usage := event.get("usage_metadata"):
                usage_stats = usage

            parts: list[JsonDict] = event.get("content", {}).get("parts", [])
            for part in parts:
                match part:
                    case {"function_call": {"name": name, "args": args}}:
                        tools_executed.append(ToolCall(step="call", tool=name, args=args))

                    case {"function_response": {"name": name, "response": response}}:
                        tools_executed.append(
                            ToolResponse(step="result", tool=name, output=response)
                        )

                    case {"text": text}:
                        try:
                            final_result = json.loads(text)
                        except json.JSONDecodeError:
                            final_result = {
                                "raw_text": text,
                                "error": "Invalid JSON",
                            }

                    case _:
                        self.logger.error("Unexpected event structure: %s", event)

        return AgentExecutionResult(
            results=final_result,
            metadata=AgentMetadata(
                tools_used=tools_executed, usage=usage_stats, event_count=len(events)
            ),
        )


if __name__ == "__main__":
    main()

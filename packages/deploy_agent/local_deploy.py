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

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

USER: str = ""
PASS: str = ""


def create_agent(errlog: str) -> LlmAgent:
    root_agent: LlmAgent = LlmAgent(
        model="gemini-2.5-flash",
        name="reddit_assistant_agent",
        instruction="Help the user fetch reddit info.",
        tools=[
            MCPToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=(
                            "python -m mcp_server_servicenow.cli"
                            ' --url "https://your-instance.service-now.com/"'
                            f" --username {USER}"
                            f" --password {PASS}"
                        ),
                    ),
                ),
                errlog=errlog,  # Required for async logging in Colab
            )
        ],
    )
    return root_agent

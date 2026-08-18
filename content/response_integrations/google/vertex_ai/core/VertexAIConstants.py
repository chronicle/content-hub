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
INTEGRATION_IDENTIFIER = "VertexAI"

# Actions
ANALYZE_EML_SCRIPT_NAME = "Analyze EML"
EXECUTE_PROMPT_SCRIPT_NAME = "Execute Prompt"
DESCRIBE_ENTITY_SCRIPT_NAME = "Describe Entity"
PING_SCRIPT_NAME = "Ping"
TRANSFORM_DATA_SCRIPT_NAME = "Transform Data"

OAUTH_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
API_ROOT_REGEX = r"https://((\w|-)+)-aiplatform.googleapis.com"
VERTEX_SDK_PUBLISHERS: list[str] = ["anthropic"]
ANTHROPIC_VERSION: str = "vertex-2023-10-16"
DEFAULT_MAX_OUTPUT_TOKENS: int = 100

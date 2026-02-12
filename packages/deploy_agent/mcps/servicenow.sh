#!/bin/bash

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

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Installing MCP ServiceNow Server"

# Install uv (a fast Python package manager)
apt-get update
apt-get install -y curl
echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH for current session
export PATH="$HOME/.local/bin:$PATH"

# Install the mcp-reddit tool using the command from its documentation
echo "Installing mcp-reddit using uv..."
uv pip install "git+https://github.com/michaelbuckner/servicenow-mcp.git" --system
echo "MCP ServiceNow Server installation complete."
#!/bin/bash
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
echo "MCP Reddit Server installation complete."
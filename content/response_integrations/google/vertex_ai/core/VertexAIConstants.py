from __future__ import annotations

INTEGRATION_IDENTIFIER = "VertexAI"

# Actions
ANALYZE_EML_SCRIPT_NAME = "Analyze EML"
EXECUTE_PROMPT_SCRIPT_NAME = "Execute Prompt"
DESCRIBE_ENTITY_SCRIPT_NAME = "Describe Entity"
PING_SCRIPT_NAME = "Ping"
TRANSFORM_DATA_SCRIPT_NAME = "Transform Data"

OAUTH_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
API_ROOT_REGEX = (
    r"https://([a-zA-Z0-9-]+)-aiplatform\.googleapis\.com|"
    r"https://aiplatform\.([a-zA-Z0-9-]+)\.rep\.googleapis\.com|"
    r"https://([a-zA-Z0-9-]+)-aiplatform\.rep\.googleapis\.com|"
    r"https://aiplatform\.googleapis\.com"
)
VERTEX_SDK_PUBLISHERS: list[str] = ["anthropic"]
ANTHROPIC_VERSION: str = "vertex-2023-10-16"
DEFAULT_MAX_OUTPUT_TOKENS: int = 100
DEFAULT_LOCATION = "us-central1"

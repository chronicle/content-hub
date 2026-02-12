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

import argparse
import logging
import os

import vertexai
from google.adk.plugins import ReflectAndRetryToolPlugin
from google.adk.plugins.logging_plugin import LoggingPlugin
from google.genai import types
from pydantic_settings import BaseSettings, SettingsConfigDict
from vertexai.agent_engines import AdkApp

from .log import setup_logging
from .settings import Settings, get_settings

logger: logging.Logger = logging.getLogger("product_agent_mesh.deployment")


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Deploy a PAM Agent to Vertex AI")
    parser.add_argument("--agent-config", required=True, help="Path to agent YAML agent")
    parser.add_argument(
        "--no-delete", action="store_false", dest="delete", help="Don't delete existing agent"
    )

    args: argparse.Namespace = parser.parse_args()
    deploy_agent(args.agent_config, delete_existing=args.delete)


def deploy_agent(config_path: str, *, delete_existing: bool = True) -> str:
    settings: Settings = get_settings()
    deploy_settings = DeploymentConfig()

    if not settings.google_cloud_project:
        msg = "GOOGLE_CLOUD_PROJECT must be set for deployment"
        raise ValueError(msg)

    bucket: str | None = deploy_settings.staging_bucket or settings.staging_bucket
    if not bucket:
        msg = "Staging bucket must be set for deployment"
        raise ValueError(msg)

    logger.info("🚀 Starting deployment for agent: %s", config_path)

    # 1. Initialize Vertex AI
    vertexai.init(project=settings.google_cloud_project, location=settings.google_cloud_region)

    client = vertexai.Client(
        project=settings.google_cloud_project,
        location=settings.google_cloud_region,
        http_options=types.HttpOptions(base_url="https://aiplatform.googleapis.com"),
    )

    # 2. Load the agent and its config
    agent = create_agent(config_path)
    conf_dict: dict[str, object] = load_config_with_secrets(config_path)
    agent_config = AgentConfig(**conf_dict)

    display_name = deploy_settings.display_name or f"PAM - {agent.name}"

    # Merge requirements
    all_requirements: list[str] = list(
        set(deploy_settings.base_requirements + agent_config.requirements)
    )

    # Expand the model name to full resource if it's a short name for Vertex AI
    if isinstance(agent.model, str) and "/" not in agent.model:
        agent.model = (
            f"projects/{settings.google_cloud_project}/locations/{settings.google_cloud_region}"
            f"/publishers/google/models/{agent.model}"
        )

    # 3. Clean up existing agents with the same name if requested
    if delete_existing:
        logger.info("🧹 Checking for existing agents with name: %s", display_name)
        for engine in client.agent_engines.list():
            if engine.api_resource.display_name == display_name:
                logger.info("🗑️ Deleting existing agent: %s", engine.api_resource.name)
                engine.delete(force=True)

    # 4. Create Remote Agent
    logger.info("📤 Uploading and creating agent engine...")
    remote_agent = client.agent_engines.create(
        agent=AdkApp(
            agent=agent,
            plugins=[
                ReflectAndRetryToolPlugin(max_retries=3),
                LoggingPlugin(),
            ],
            enable_tracing=True,
        ),
        config={
            "display_name": display_name,
            "description": deploy_settings.description,
            "staging_bucket": bucket,
            "gcs_dir_name": deploy_settings.gcs_dir_name,
            "requirements": all_requirements,
            "env_vars": {
                "GOOGLE_CLOUD_PROJECT": settings.google_cloud_project,
                "GOOGLE_CLOUD_REGION": settings.google_cloud_region,
                "ENVIRONMENT": "production",
                # Include only env vars declared by this agent in `required_env_vars`
                **{
                    k: v
                    for k in agent_config.required_env_vars
                    if (v := os.environ.get(k)) is not None
                },
                # Pass global settings
                **{
                    k: v
                    for k in ["GOOGLE_API_KEY", "LOG_LEVEL"]
                    if (v := os.environ.get(k)) is not None
                },
            },
        },
    )

    agent_id = remote_agent.api_resource.name.split("/")[-1]
    logger.info("✅ Deployment successful! Agent Engine ID: %s", agent_id)
    return agent_id


class DeploymentConfig(BaseSettings):
    display_name: str | None = None
    description: str = "Product Agent Mesh Node"
    staging_bucket: str | None = None
    gcs_dir_name: str = "adk_deployment"

    # Base requirements for any agent
    base_requirements: list[str] = [
        "google-cloud-aiplatform[agent_engines,adk]>=1.78.0",
        "google-adk>=1.18.0",
        "mcp>=1.2.0",
        "httpx>=0.28.0",
        "pydantic>=2.0.0",
        "pydantic-settings",
        "pyyaml",
    ]

    model_config = SettingsConfigDict(env_prefix="DEPLOY_", extra="ignore")


if __name__ == "__main__":
    main()
